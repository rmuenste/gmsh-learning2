#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


def find_vtk_in_geo(geo_path: Path) -> Path | None:
    pattern = re.compile(r"^\s*Save\s+[\"']([^\"']+\.vtk)[\"']\s*;", re.IGNORECASE)
    vtk_rel = None
    with geo_path.open("r", encoding="utf-8") as f:
        for line in f:
            m = pattern.search(line)
            if m:
                vtk_rel = m.group(1)
    if not vtk_rel:
        return None
    vtk_path = Path(vtk_rel)
    if not vtk_path.is_absolute():
        vtk_path = (geo_path.parent / vtk_path).resolve()
    return vtk_path


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run .geo -> VTK -> TRI -> case folder -> VTU workflow")
    parser.add_argument("geo", help="Path to .geo file")
    parser.add_argument("--gmsh", default="gmsh", help="gmsh executable (default: gmsh)")
    parser.add_argument("--vtk", default="", help="Override expected VTK output path")
    parser.add_argument("--outdir", default="", help="Output case folder path")
    parser.add_argument("--gmsh-args", default="", help="Extra args passed to gmsh (quoted string)")
    args = parser.parse_args()

    geo_path = Path(args.geo).resolve()
    if not geo_path.exists():
        print(f"Error: .geo not found: {geo_path}", file=sys.stderr)
        return 1

    # 1) Run gmsh on the .geo
    gmsh_cmd = [args.gmsh, str(geo_path), "-3"]
    if args.gmsh_args:
        gmsh_cmd.extend(args.gmsh_args.split())
    run(gmsh_cmd)

    # 2) Resolve VTK output
    vtk_path = Path(args.vtk).resolve() if args.vtk else find_vtk_in_geo(geo_path)
    if vtk_path is None:
        print("Error: could not find a Save \"...vtk\" statement in the .geo.", file=sys.stderr)
        print("Provide --vtk /path/to/output.vtk or add Save \"...vtk\"; to the .geo.", file=sys.stderr)
        return 1
    if not vtk_path.exists():
        print(f"Error: expected VTK not found: {vtk_path}", file=sys.stderr)
        return 1

    # 3) VTK -> TRI (hex-only)
    tri_path = vtk_path.with_suffix(".tri")
    run([sys.executable, "pe_partpy/tri2vtk_converter.py", str(vtk_path), str(tri_path)])

    # 4) TRI -> case folder (regions + file.prj)
    gen_par_cmd = [sys.executable, "pe_partpy/gen_par_from_tri_by_normals.py", str(tri_path)]
    case_dir = None
    if args.outdir:
        case_dir = Path(args.outdir).resolve()
        gen_par_cmd.extend(["--outdir", str(case_dir)])
    run(gen_par_cmd)

    # 5) case folder -> VTU for visualization
    if case_dir is None:
        case_dir = tri_path.with_suffix("")
    prj_path = case_dir / "file.prj"
    if not prj_path.exists():
        print(f"Error: expected project file not found: {prj_path}", file=sys.stderr)
        return 1
    run([sys.executable, "pe_partpy/tri2vtk_converter.py", str(prj_path), "-proj", str(case_dir)])

    print(f"Done. Output case folder: {case_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
