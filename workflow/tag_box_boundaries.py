#!/usr/bin/env python3
"""
Tag the six face regions of an axis-aligned box case with analytic
plane descriptors for the CFD application.

Expects a case folder produced by gen_par_from_tri.py (xmin/xmax/ymin/
ymax/zmin/zmax.par + file.prj). Infers the box bounds from the .tri,
verifies each region's nodes lie on its plane, then rewrites each .par
parameter line with a quoted type-4 plane descriptor:

    '4 dA dB dC dD'   for the plane dA*x + dB*y + dC*z + dD = 0

The descriptor line must stay quoted: the CFD reads it with a Fortran
list-directed READ, which would otherwise stop at the first blank.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from pe_partpy.mesh.mesh_io import readTriFile

FACES = ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax")


def _fmt(value: float) -> str:
    text = f"{value:.15g}"
    return f"{text}d0"


def _plane_descriptor(face: str, bounds: dict[str, float]) -> str:
    axis = face[0]
    normal = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}[axis]
    offset = -bounds[face] + 0.0  # +0.0 normalizes -0.0
    parts = " ".join(_fmt(v) for v in (*normal, offset))
    return f"'4 {parts}'"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--case-dir", required=True, help="Case folder with file.prj + <face>.par files")
    parser.add_argument("--btype", default="Wall", help="Boundary type for all six faces (default: Wall)")
    parser.add_argument("--tol", type=float, default=1e-9, help="Plane membership tolerance (default: 1e-9)")
    args = parser.parse_args()

    case_dir = Path(args.case_dir).resolve()
    prj_path = case_dir / "file.prj"
    if not prj_path.exists():
        print(f"Error: project file not found: {prj_path}", file=sys.stderr)
        return 1
    tri_name = prj_path.read_text().splitlines()[0].strip()
    mesh = readTriFile(str(case_dir / tri_name))
    nodes = mesh.nodes

    bounds = {
        "xmin": min(float(p[0]) for p in nodes),
        "xmax": max(float(p[0]) for p in nodes),
        "ymin": min(float(p[1]) for p in nodes),
        "ymax": max(float(p[1]) for p in nodes),
        "zmin": min(float(p[2]) for p in nodes),
        "zmax": max(float(p[2]) for p in nodes),
    }
    axis_index = {"x": 0, "y": 1, "z": 2}

    for face in FACES:
        par_path = case_dir / f"{face}.par"
        if not par_path.exists():
            print(f"Error: expected {par_path} (axis-aligned box case)", file=sys.stderr)
            return 1
        lines = par_path.read_text().splitlines()
        node_ids = [int(line) for line in lines[2:] if line.strip()]
        ax = axis_index[face[0]]
        worst = max(abs(float(nodes[nid - 1][ax]) - bounds[face]) for nid in node_ids)
        if worst >= args.tol:
            print(
                f"Error: {face}.par has nodes off its plane "
                f"(max deviation {worst:.3e} >= tol {args.tol:.1e})",
                file=sys.stderr,
            )
            return 1
        descriptor = _plane_descriptor(face, bounds)
        lines[0] = f"{len(node_ids)} {args.btype}"
        lines[1] = descriptor
        par_path.write_text("\n".join(lines) + "\n")
        print(f"{face}.par: {len(node_ids)} nodes, btype {args.btype}, parameter {descriptor}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
