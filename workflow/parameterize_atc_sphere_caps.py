#!/usr/bin/env python3
"""
Fit fixed-radius spheres to the two open ends of an ATC helix case and
annotate the matching region_####.par files for the CFD application.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pe_partpy.gen_par_from_tri_by_normals import compute_boundary_regions


def _face_edges(face_nodes: tuple[int, int, int, int]) -> list[tuple[int, int]]:
    v0, v1, v2, v3 = face_nodes
    return [
        tuple(sorted((v0, v1))),
        tuple(sorted((v1, v2))),
        tuple(sorted((v2, v3))),
        tuple(sorted((v3, v0))),
    ]


def _region_stats(
    nodes: list[np.ndarray],
    face_nodes: list[tuple[int, int, int, int]],
    normals: list[np.ndarray],
    components: list[list[int]],
) -> list[dict]:
    stats = []
    for ridx, faces in enumerate(components):
        node_ids = sorted({vid for fidx in faces for vid in face_nodes[fidx]})
        pts = np.stack([nodes[vid] for vid in node_ids], axis=0)
        avg_normal = np.zeros(3, dtype=float)
        for fidx in faces:
            avg_normal += normals[fidx]
        norm = np.linalg.norm(avg_normal)
        if norm > 0.0:
            avg_normal = avg_normal / norm
        stats.append(
            {
                "region_idx": ridx,
                "node_ids": node_ids,
                "centroid": pts.mean(axis=0),
                "avg_normal": avg_normal,
                "face_count": len(faces),
            }
        )
    return stats


def _helix_point(theta: float, radius: float, pitch_per_turn: float, z0: float) -> np.ndarray:
    k = pitch_per_turn / (2.0 * math.pi)
    return np.array(
        [radius * math.cos(theta), radius * math.sin(theta), z0 + k * theta],
        dtype=float,
    )


def _pick_endpoint_regions(
    stats: list[dict],
    start_pt: np.ndarray,
    end_pt: np.ndarray,
) -> tuple[int, int]:
    start_order = sorted(
        stats,
        key=lambda item: float(np.linalg.norm(item["centroid"] - start_pt)),
    )
    end_order = sorted(
        stats,
        key=lambda item: float(np.linalg.norm(item["centroid"] - end_pt)),
    )
    start_idx = start_order[0]["region_idx"]
    end_idx = next(item["region_idx"] for item in end_order if item["region_idx"] != start_idx)
    return start_idx, end_idx


def _extract_ring_node_ids(
    face_nodes: list[tuple[int, int, int, int]],
    component_faces: list[int],
) -> list[int]:
    edge_counts: dict[tuple[int, int], int] = {}
    for fidx in component_faces:
        for edge in _face_edges(face_nodes[fidx]):
            edge_counts[edge] = edge_counts.get(edge, 0) + 1

    ring_nodes = {
        vid
        for edge, count in edge_counts.items()
        if count == 1
        for vid in edge
    }
    return sorted(ring_nodes)


def _write_points_csv(path: Path, node_ids: list[int], nodes: list[np.ndarray]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["vtkOriginalPointIds", "Points:0", "Points:1", "Points:2"])
        for node_id in node_ids:
            p = nodes[node_id]
            writer.writerow([node_id + 1, float(p[0]), float(p[1]), float(p[2])])


def _parse_fit_output(output: str) -> dict:
    theta_match = re.search(r"theta_min \(deg\)\s*=\s*([^\n]+)", output)
    center_match = re.search(r"Center C\s*=\s*\[([^\]]+)\]", output)
    rmse_match = re.search(r"RMSE\(\|p-C\|-r\)\s*=\s*([^\n]+)", output)
    residual_match = re.search(r"min/max residual\s*=\s*\[([^,]+),\s*([^\]]+)\]", output)
    free_center_matches = re.findall(r"Center C_free\s*=\s*\[([^\]]+)\]", output)
    free_rmse_matches = re.findall(r"RMSE\(\|p-C\|-r\)\s*=\s*([^\n]+)", output)
    free_residual_matches = re.findall(r"min/max residual\s*=\s*\[([^,]+),\s*([^\]]+)\]", output)

    if not (center_match and theta_match and rmse_match and residual_match):
        raise RuntimeError(f"Unexpected fit_sphere_centerline.py output:\n{output}")

    # When free refinement is enabled, prefer the second-pass center and metrics.
    if free_center_matches:
        center = [float(part.strip()) for part in free_center_matches[-1].split(",")]
        rmse_value = float(free_rmse_matches[-1].strip())
        residual_min = float(free_residual_matches[-1][0].strip())
        residual_max = float(free_residual_matches[-1][1].strip())
        free_refined = True
    else:
        center = [float(part.strip()) for part in center_match.group(1).split(",")]
        rmse_value = float(rmse_match.group(1).strip())
        residual_min = float(residual_match.group(1).strip())
        residual_max = float(residual_match.group(2).strip())
        free_refined = False

    return {
        "center": center,
        "theta_deg": float(theta_match.group(1).strip()),
        "rmse": rmse_value,
        "residual_min": residual_min,
        "residual_max": residual_max,
        "free_refined": free_refined,
    }


def _run_fit(
    fit_script: Path,
    ring_csv: Path,
    theta_center_deg: float,
    radius: float,
    helix_radius: float,
    pitch_per_turn: float,
    z0: float,
    search_halfwidth_deg: float,
    free_dx_max: float,
    free_dy_max: float,
    free_dz_max: float,
    free_iters: int,
) -> dict:
    theta_min_deg = theta_center_deg - search_halfwidth_deg
    theta_max_deg = theta_center_deg + search_halfwidth_deg
    cmd = [
        sys.executable,
        str(fit_script),
        "--ring_csv",
        str(ring_csv),
        "--R",
        str(helix_radius),
        "--Pturn",
        str(pitch_per_turn),
        "--z0",
        str(z0),
        "--r",
        str(radius),
        "--theta_center",
        str(math.radians(theta_center_deg)),
        "--theta_halfwidth_deg",
        str(search_halfwidth_deg),
        "--theta_min_deg",
        str(theta_min_deg),
        "--theta_max_deg",
        str(theta_max_deg),
        "--free_dx_max",
        str(free_dx_max),
        "--free_dy_max",
        str(free_dy_max),
        "--free_dz_max",
        str(free_dz_max),
        "--free_iters",
        str(free_iters),
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return _parse_fit_output(result.stdout)


def _rewrite_par_parameter(path: Path, parameter_line: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 2:
        raise RuntimeError(f"Unexpected .par file format: {path}")
    lines[1] = parameter_line
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Fit sphere caps to the start and end regions of an ATC helix case",
    )
    ap.add_argument("tri", type=Path, help="Path to input .tri file")
    ap.add_argument("--case-dir", type=Path, required=True, help="Case directory containing region_####.par files")
    ap.add_argument("--R", type=float, required=True, help="Helix radius")
    ap.add_argument("--Pturn", type=float, required=True, help="Pitch per full turn")
    ap.add_argument("--start-angle-deg", type=float, required=True, help="Helix start angle in degrees")
    ap.add_argument("--end-angle-deg", type=float, required=True, help="Helix end angle in degrees")
    ap.add_argument("--sphere-radius", type=float, default=10.0, help="Sphere radius for both end caps")
    ap.add_argument("--z0", type=float, default=0.0, help="Helix z offset at theta=0")
    ap.add_argument("--delta", type=float, default=30.0, help="Boundary clustering angle in degrees")
    ap.add_argument("--min-faces", type=int, default=0, help="Merge-small-regions threshold")
    ap.add_argument(
        "--search-halfwidth-deg",
        type=float,
        default=90.0,
        help="Search half-width around each endpoint along the centerline",
    )
    ap.add_argument("--free-dx-max", type=float, default=0.0, help="Optional second-pass x refinement half-width")
    ap.add_argument("--free-dy-max", type=float, default=0.0, help="Optional second-pass y refinement half-width")
    ap.add_argument("--free-dz-max", type=float, default=0.0, help="Optional second-pass z refinement half-width")
    ap.add_argument(
        "--free-iters",
        type=int,
        default=2,
        help="Coordinate-descent cycles for second-pass free dx/dy/dz refinement",
    )
    ap.add_argument(
        "--sidecar-name",
        default="sphere_regions.json",
        help="JSON sidecar written into the case directory",
    )
    args = ap.parse_args()

    tri_path = args.tri.resolve()
    case_dir = args.case_dir.resolve()
    fit_script = Path(__file__).resolve().parent.parent / "gmsh-learning" / "fit_sphere_centerline.py"

    if not tri_path.exists():
        raise SystemExit(f".tri file not found: {tri_path}")
    if not case_dir.exists():
        raise SystemExit(f"Case directory not found: {case_dir}")
    if not fit_script.exists():
        raise SystemExit(f"fit_sphere_centerline.py not found: {fit_script}")

    region_data = compute_boundary_regions(tri_path, delta=args.delta, min_faces=args.min_faces)
    mesh = region_data["mesh"]
    face_nodes = region_data["face_nodes"]
    normals = region_data["normals"]
    components = region_data["components"]

    stats = _region_stats(mesh.nodes, face_nodes, normals, components)
    start_theta = math.radians(args.start_angle_deg)
    end_theta = math.radians(args.end_angle_deg)
    start_pt = _helix_point(start_theta, args.R, args.Pturn, args.z0)
    end_pt = _helix_point(end_theta, args.R, args.Pturn, args.z0)
    start_region_idx, end_region_idx = _pick_endpoint_regions(stats, start_pt, end_pt)

    endpoint_specs = [
        ("start", start_region_idx, args.start_angle_deg),
        ("end", end_region_idx, args.end_angle_deg),
    ]

    sidecar_entries = []
    with tempfile.TemporaryDirectory(prefix="atc_sphere_caps_") as tmpdir:
        tmpdir_path = Path(tmpdir)
        for endpoint_name, region_idx, theta_center_deg in endpoint_specs:
            ring_node_ids = _extract_ring_node_ids(face_nodes, components[region_idx])
            if not ring_node_ids:
                raise RuntimeError(f"Could not extract ring nodes for {endpoint_name} region {region_idx}")

            ring_csv = tmpdir_path / f"{endpoint_name}_ring.csv"
            _write_points_csv(ring_csv, ring_node_ids, mesh.nodes)
            fit_result = _run_fit(
                fit_script=fit_script,
                ring_csv=ring_csv,
                theta_center_deg=theta_center_deg,
                radius=args.sphere_radius,
                helix_radius=args.R,
                pitch_per_turn=args.Pturn,
                z0=args.z0,
                search_halfwidth_deg=args.search_halfwidth_deg,
                free_dx_max=args.free_dx_max,
                free_dy_max=args.free_dy_max,
                free_dz_max=args.free_dz_max,
                free_iters=args.free_iters,
            )

            region_id = region_idx
            par_name = f"region_{region_idx + 1:04d}.par"
            par_path = case_dir / par_name
            if not par_path.exists():
                raise RuntimeError(f"Expected region file not found: {par_path}")

            _rewrite_par_parameter(par_path, f"-3 {region_id}")
            sidecar_entries.append(
                {
                    "region_id": region_id,
                    "par_file": par_name,
                    "endpoint": endpoint_name,
                    "center": fit_result["center"],
                    "radius": args.sphere_radius,
                    "theta_deg": fit_result["theta_deg"],
                    "rmse": fit_result["rmse"],
                    "residual_min": fit_result["residual_min"],
                    "residual_max": fit_result["residual_max"],
                    "free_refined": fit_result["free_refined"],
                    "ring_node_count": len(ring_node_ids),
                }
            )

    sidecar = {
        "version": 1,
        "tri_file": tri_path.name,
        "fit_settings": {
            "sphere_radius": args.sphere_radius,
            "search_halfwidth_deg": args.search_halfwidth_deg,
            "free_dx_max": args.free_dx_max,
            "free_dy_max": args.free_dy_max,
            "free_dz_max": args.free_dz_max,
            "free_iters": args.free_iters,
        },
        "sphere_regions": sorted(sidecar_entries, key=lambda item: item["region_id"]),
    }
    sidecar_path = case_dir / args.sidecar_name
    sidecar_path.write_text(json.dumps(sidecar, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote sphere sidecar: {sidecar_path}")
    for entry in sidecar["sphere_regions"]:
        print(
            f"Parameterized {entry['par_file']} as spherical region {entry['region_id']} "
            f"with center {entry['center']} and radius {entry['radius']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
