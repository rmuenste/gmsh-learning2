#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def default_mesh_name(project_file: Path, strategy: str, subdivision_spec: str) -> str:
    safe_spec = subdivision_spec.replace("@", "abs").replace("[", "_").replace("]", "_")
    safe_spec = safe_spec.replace(",", "_").replace("-", "__")
    safe_spec = "".join(char if char.isalnum() or char in "._-" else "_" for char in safe_spec)
    return f"{project_file.parent.name}_{strategy}_{safe_spec}".strip("_")


def convert_subpartitions_to_vtu(repo_root: Path, output_dir: Path) -> list[Path]:
    sys.path.insert(0, str(repo_root / "pe_partpy"))
    import tri2vtk_converter as tri2vtk  # pylint: disable=import-outside-toplevel

    subpartition_vtus: list[Path] = []
    for subdir in sorted(path for path in output_dir.iterdir() if path.is_dir() and path.name.startswith("sub")):
        tri_name, par_info = tri2vtk.process_dev_directory(str(subdir))
        tri_path = subdir / tri_name
        tri_files = sorted(subdir.glob("GRID*.tri"))
        for tri_file in tri_files:
            if tri_file.name == tri_name:
                continue
            vtu_path = tri_file.with_suffix(".vtu")
            tri2vtk.convertTri2VtkXml(str(tri_file), str(vtu_path), par_info)
            subpartition_vtus.append(vtu_path)

        if not tri_files:
            raise FileNotFoundError(f"No GRID*.tri files found in subpartition directory {subdir}")
        if not tri_path.exists():
            raise FileNotFoundError(f"Expected main TRI file not found in {subdir}: {tri_path}")

    return subpartition_vtus


def write_pvd_collection(output_dir: Path, vtu_paths: list[Path], pvd_name: str = "subdomains.pvd") -> Path:
    pvd_path = output_dir / pvd_name
    with pvd_path.open("w", encoding="utf-8") as fh:
        fh.write("<?xml version=\"1.0\"?>\n")
        fh.write("<VTKFile type=\"Collection\" version=\"0.1\" byte_order=\"LittleEndian\">\n")
        fh.write("  <Collection>\n")
        for idx, vtu_path in enumerate(vtu_paths):
            rel_path = vtu_path.relative_to(output_dir).as_posix()
            fh.write(
                f"    <DataSet timestep=\"0\" part=\"{idx}\" file=\"{escape(rel_path)}\"/>\n"
            )
        fh.write("  </Collection>\n")
        fh.write("</VTKFile>\n")
    return pvd_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run PyPartitioner on a case folder and then generate a ParaView VTU."
    )
    parser.add_argument("project_file", help="Path to case project file (.prj)")
    parser.add_argument("n_part", type=int, help="Number of partitions")
    parser.add_argument("strategy", help="Partitioning strategy name")
    parser.add_argument("subdivision_spec", help="Subdivision spec passed to PyPartitioner")
    parser.add_argument(
        "--mesh-name",
        default="",
        help="Output name under _mesh/. Defaults to a name derived from the case folder and strategy.",
    )
    parser.add_argument(
        "--format",
        default="v2",
        help="Subdirectory numbering format passed through to PyPartitioner (default: v2)",
    )
    parser.add_argument(
        "--skip-subdomain-vtu",
        action="store_true",
        help="Skip per-subpartition VTU generation and only write the combined main.vtu.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    project_file = Path(args.project_file).resolve()
    if not project_file.exists():
        print(f"Error: project file not found: {project_file}", file=sys.stderr)
        return 1

    mesh_name = args.mesh_name or default_mesh_name(project_file, args.strategy, args.subdivision_spec)
    output_dir = repo_root / "_mesh" / mesh_name

    run(
        [
            sys.executable,
            "pe_partpy/PyPartitioner.py",
            str(args.n_part),
            args.strategy,
            args.subdivision_spec,
            mesh_name,
            str(project_file),
            "-f",
            args.format,
        ]
    )

    project_output = output_dir / "GRID.prj"
    if not project_output.exists():
        print(f"Error: expected partitioned project file not found: {project_output}", file=sys.stderr)
        return 1

    run(
        [
            sys.executable,
            "pe_partpy/tri2vtk_converter.py",
            str(project_output),
            "-proj",
            str(output_dir),
        ]
    )

    subpartition_vtus: list[Path] = []
    pvd_path: Path | None = None
    if not args.skip_subdomain_vtu:
        subpartition_vtus = convert_subpartitions_to_vtu(repo_root, output_dir)
        pvd_path = write_pvd_collection(output_dir, subpartition_vtus)

    print(f"Done. Partitioned case folder: {output_dir}")
    print(f"ParaView file: {output_dir / 'main.vtu'}")
    if subpartition_vtus:
        print(f"Per-subpartition VTU files: {len(subpartition_vtus)}")
    if pvd_path is not None:
        print(f"Subpartition collection: {pvd_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
