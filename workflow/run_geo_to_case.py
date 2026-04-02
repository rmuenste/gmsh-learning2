#!/usr/bin/env python3
import argparse
import re
import subprocess
import sys
import tempfile
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


def rewrite_geo_save_path(geo_path: Path, vtk_path: Path) -> Path:
    pattern = re.compile(r'^\s*Save\s+["\']([^"\']+\.vtk)["\']\s*;.*$', re.IGNORECASE)
    new_lines = []
    replaced = False
    with geo_path.open("r", encoding="utf-8") as f:
        for line in f:
            match = pattern.match(line)
            if match:
                indent = line[: len(line) - len(line.lstrip())]
                new_lines.append(f'{indent}Save "{vtk_path}";\n')
                replaced = True
            else:
                new_lines.append(line)
    if not replaced:
        raise ValueError(f'Could not find Save "...vtk" statement in {geo_path}')

    temp_dir = Path(tempfile.mkdtemp(prefix="run_geo_to_case_"))
    temp_geo = temp_dir / geo_path.name
    temp_geo.write_text("".join(new_lines), encoding="utf-8")
    return temp_geo


def parse_setnumber(items: list[str]) -> list[tuple[str, str]]:
    parsed: list[tuple[str, str]] = []
    for item in items:
        if "=" not in item:
            raise ValueError(f"Invalid --setnumber value '{item}'. Expected name=value.")
        name, value = item.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name or not value:
            raise ValueError(f"Invalid --setnumber value '{item}'. Expected name=value.")
        parsed.append((name, value))
    return parsed


def build_override_suffix(pairs: list[tuple[str, str]]) -> str:
    parts = []
    for name, value in pairs:
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", name)
        safe_value = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
        parts.append(f"{safe_name}-{safe_value}")
    return "__".join(parts)


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
    parser.add_argument(
        "--setnumber",
        action="append",
        default=[],
        help="Pass Gmsh ONELAB overrides as name=value; may be specified multiple times",
    )
    args = parser.parse_args()

    geo_path = Path(args.geo).resolve()
    if not geo_path.exists():
        print(f"Error: .geo not found: {geo_path}", file=sys.stderr)
        return 1

    try:
        setnumber_pairs = parse_setnumber(args.setnumber)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    vtk_path = Path(args.vtk).resolve() if args.vtk else find_vtk_in_geo(geo_path)
    if vtk_path is None:
        print('Error: could not find a Save "...vtk" statement in the .geo.', file=sys.stderr)
        print("Provide --vtk /path/to/output.vtk or add Save \"...vtk\"; to the .geo.", file=sys.stderr)
        return 1

    run_geo_path = geo_path
    if setnumber_pairs and not args.vtk:
        suffix = build_override_suffix(setnumber_pairs)
        vtk_path = vtk_path.with_name(f"{vtk_path.stem}__{suffix}{vtk_path.suffix}")
        try:
            run_geo_path = rewrite_geo_save_path(geo_path, vtk_path)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    # 1) Run gmsh on the .geo
    gmsh_cmd = [args.gmsh, str(run_geo_path), "-3"]
    if args.gmsh_args:
        gmsh_cmd.extend(args.gmsh_args.split())
    for name, value in setnumber_pairs:
        gmsh_cmd.extend(["-setnumber", name, value])
    run(gmsh_cmd)

    # 2) Resolve VTK output
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
