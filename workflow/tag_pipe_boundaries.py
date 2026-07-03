#!/usr/bin/env python3
"""
Tag the boundary regions of a z-axis pipe case for periodic CFD runs.

Expects a case folder produced by gen_par_from_tri_by_normals.py (three
regions: cylindrical hull + two flat end caps). Classifies the regions
from node coordinates, verifies the end faces are exact translated
copies of each other, then rewrites the .par headers:

  hull:  <count> Wall      + analytic cylinder descriptor (type 7)
  caps:  <count> Periodic  + ''   (non-BC tag; coupling is done by
                                   coordinate matching, dPeriodicity(3)=L)

Finally renames the files to hull.par / zmin.par / zmax.par and rewrites
file.prj accordingly.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pe_partpy.mesh.mesh_io import readTriFile

DEFAULT_HULL_PARAM = "7 0d0 0d0 0d0 0.5d0 1d0 1d0 0d0"


def _read_par(path: Path) -> tuple[str, str, list[int]]:
    lines = path.read_text().splitlines()
    if len(lines) < 2:
        raise ValueError(f"{path}: malformed .par file (fewer than 2 lines)")
    header = lines[0]
    parameter = lines[1]
    node_ids = [int(line) for line in lines[2:] if line.strip()]
    count = int(header.split()[0])
    if count != len(node_ids):
        raise ValueError(f"{path}: header count {count} != node lines {len(node_ids)}")
    return header, parameter, node_ids


def _write_par(path: Path, btype: str, parameter: str, node_ids: list[int]) -> None:
    lines = [f"{len(node_ids)} {btype}", parameter]
    lines.extend(str(nid) for nid in node_ids)
    path.write_text("\n".join(lines) + "\n")


def _classify_regions(
    regions: dict[str, list[int]],
    nodes,
    tol: float,
) -> dict[str, str]:
    zmin_v = min(float(p[2]) for p in nodes)
    zmax_v = max(float(p[2]) for p in nodes)
    r_mesh = max(math.hypot(float(p[0]), float(p[1])) for p in nodes)

    labels: dict[str, str] = {}
    for name, node_ids in regions.items():
        pts = [nodes[nid - 1] for nid in node_ids]
        if all(abs(float(p[2]) - zmin_v) < tol for p in pts):
            label = "zmin"
        elif all(abs(float(p[2]) - zmax_v) < tol for p in pts):
            label = "zmax"
        elif all(abs(math.hypot(float(p[0]), float(p[1])) - r_mesh) < tol for p in pts):
            label = "hull"
        else:
            raise SystemExit(
                f"Error: region {name} is neither a z={zmin_v}/z={zmax_v} cap "
                f"nor an r={r_mesh} hull (tol={tol}). Not a clean pipe case."
            )
        if label in labels.values():
            raise SystemExit(f"Error: two regions classify as '{label}'.")
        labels[name] = label

    missing = {"hull", "zmin", "zmax"} - set(labels.values())
    if missing:
        raise SystemExit(
            f"Error: expected exactly regions hull/zmin/zmax, missing: {sorted(missing)}. "
            f"Got {len(regions)} regions: {labels}"
        )
    return labels


def _check_congruence(
    zmin_ids: list[int],
    zmax_ids: list[int],
    nodes,
    length: float,
    tol: float,
) -> None:
    if len(zmin_ids) != len(zmax_ids):
        raise SystemExit(
            f"Error: end faces have different node counts "
            f"({len(zmin_ids)} vs {len(zmax_ids)}) - not congruent."
        )
    lo = sorted(
        (round(float(nodes[nid - 1][0]), 12), round(float(nodes[nid - 1][1]), 12))
        for nid in zmin_ids
    )
    hi = sorted(
        (round(float(nodes[nid - 1][0]), 12), round(float(nodes[nid - 1][1]), 12))
        for nid in zmax_ids
    )
    worst = 0.0
    for (x0, y0), (x1, y1) in zip(lo, hi):
        worst = max(worst, abs(x0 - x1), abs(y0 - y1))
    if worst >= tol:
        raise SystemExit(
            f"Error: end faces are not translated copies "
            f"(max in-plane mismatch {worst:.3e} >= tol {tol:.1e})."
        )
    print(f"End-face congruence OK: {len(zmin_ids)} nodes/face, "
          f"translation (0,0,{length}), max in-plane mismatch {worst:.3e}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--case-dir", required=True, help="Case folder with file.prj + region_*.par")
    parser.add_argument("--tri", default="", help="Path to the .tri (default: first line of file.prj)")
    parser.add_argument("--tol", type=float, default=1e-6, help="Coordinate tolerance (default: 1e-6)")
    parser.add_argument(
        "--hull-param",
        default=DEFAULT_HULL_PARAM,
        help=f"Analytic hull parametrization line (default: '{DEFAULT_HULL_PARAM}')",
    )
    args = parser.parse_args()

    case_dir = Path(args.case_dir).resolve()
    prj_path = case_dir / "file.prj"
    if not prj_path.exists():
        print(f"Error: project file not found: {prj_path}", file=sys.stderr)
        return 1

    prj_lines = [line.strip() for line in prj_path.read_text().splitlines() if line.strip()]
    tri_name = prj_lines[0]
    par_names = prj_lines[1:]

    tri_path = Path(args.tri).resolve() if args.tri else case_dir / tri_name
    if not tri_path.exists():
        print(f"Error: .tri not found: {tri_path}", file=sys.stderr)
        return 1

    mesh = readTriFile(str(tri_path))
    nodes = mesh.nodes
    length = max(float(p[2]) for p in nodes) - min(float(p[2]) for p in nodes)

    regions: dict[str, list[int]] = {}
    parameters: dict[str, str] = {}
    for name in par_names:
        _, parameter, node_ids = _read_par(case_dir / name)
        regions[name] = node_ids
        parameters[name] = parameter

    labels = _classify_regions(regions, nodes, args.tol)
    by_label = {label: name for name, label in labels.items()}

    _check_congruence(regions[by_label["zmin"]], regions[by_label["zmax"]], nodes, length, args.tol)

    renames = {"hull": "hull.par", "zmin": "zmin.par", "zmax": "zmax.par"}
    for label, new_name in renames.items():
        old_name = by_label[label]
        old_path = case_dir / old_name
        new_path = case_dir / new_name
        node_ids = regions[old_name]
        if label == "hull":
            _write_par(new_path, "Wall", args.hull_param, node_ids)
        else:
            _write_par(new_path, "Periodic", "''", node_ids)
        if new_path != old_path:
            old_path.unlink()
        print(f"{old_name} -> {new_name}: {len(node_ids)} nodes, "
              f"btype {'Wall' if label == 'hull' else 'Periodic'}")

    prj_path.write_text("\n".join([tri_name, "hull.par", "zmin.par", "zmax.par"]) + "\n")
    print(f"Rewrote {prj_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
