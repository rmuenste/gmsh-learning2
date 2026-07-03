# Gmsh to CFD Workflow

Unified workflow for generating, converting, and preparing hexahedral meshes for CFD applications.

## Overview

This project integrates:
- **gmsh-learning**: Gmsh scripts for helical and structured hex mesh generation
- **pe_partpy**: Python tools for mesh partitioning and I/O
- **workflow**: Driver scripts unifying the mesh generation pipeline

## Quick Start

```bash
# 1. Run setup check (clones subrepos if missing)
./setup.sh

# 1b. Verify CLI + venv deps (recommended)
./workflow/check_env.sh

# 2. Generate a mesh (example: structured box)
gmsh workflow/generators/simple_box.geo -3 -o out/box/mesh.msh

# 3. Convert to VTK and TRI formats
python3 workflow/converters/msh_to_vtk.py out/box/mesh.msh

# 4. Generate boundary parametrization (writes out/box/mesh_regions/)
python3 pe_partpy/gen_par_from_tri_regions.py out/box/mesh.tri

# 5. Visualize in ParaView
python3 pe_partpy/tri2vtk_converter.py out/box/mesh_regions/file.prj \
    -proj out/box/mesh_regions
paraview out/box/mesh_regions/main.vtu
```

## One-shot workflow (.geo → case folder)

```bash
.venv/bin/python workflow/run_geo_to_case.py gmsh-learning/examples/pure_quad_omesh_helix_minimal_bl1.geo
```

With explicit output folder:
```bash
.venv/bin/python workflow/run_geo_to_case.py gmsh-learning/examples/pure_quad_omesh_helix_minimal_bl1.geo --outdir gmsh-learning/output/my_case
```

Note: the `.geo` must contain a `Save "...vtk";` statement (the helix examples do). See `workflow/README.md` for parameterized runs (`--setnumber`) and ATC sphere-cap fitting (`--fit-atc-spheres`).

## Partition a case and inspect it

```bash
python3 workflow/run_partition_to_vtu.py <case_dir>/file.prj 4 metis_recursive 1
paraview _mesh/<mesh-name>/main.vtu
```

## Project Structure

```
gmsh-learning2/
├── README.md                 # This file
├── setup.sh                  # Subrepo setup + environment checker
├── .gitignore               # Git ignore patterns
│
├── workflow/                 # Unified workflow scripts
│   ├── README.md            # Detailed workflow documentation
│   ├── check_env.sh         # Environment check
│   ├── run_geo_to_case.py   # .geo → VTK → TRI → case folder pipeline
│   ├── run_partition_to_vtu.py  # Partition a case + generate VTUs
│   ├── parameterize_atc_sphere_caps.py  # ATC sphere-cap fitting
│   ├── generators/          # Gmsh .geo mesh generation scripts
│   │   ├── simple_box.geo           # Structured hex box
│   │   ├── box_hex.geo              # Hex box variant
│   │   ├── cylinder_structured.geo  # O-grid cylinder with hole
│   │   ├── cylinder_hex.geo         # Hex cylinder
│   │   └── glowinski_column.geo     # Glowinski column geometry
│   └── converters/          # Format conversion utilities
│       └── msh_to_vtk.py    # MSH 4.x → VTK + TRI converter
│
├── _mesh/                    # Partitioning output (created at runtime)
│
├── gmsh-learning/           # Separate git repo: Helical mesh generation
│   └── (external repo)
│
└── pe_partpy/               # Separate git repo: Mesh partitioning
    ├── PyPartitioner.py                 # Partitioning entry point
    ├── mesh/mesh_io.py                  # Includes MSH 4.x readers
    ├── gen_par_from_tri.py              # Axis-aligned boundary detection
    ├── gen_par_from_tri_by_normals.py   # Normal-clustering boundary detection
    ├── gen_par_from_tri_regions.py      # Region-growing boundary detection
    └── tri2vtk_converter.py             # VTK ↔ TRI conversion + VTU output
```

## Dependencies

- **Gmsh 4.x (CLI)**: Mesh generation ([gmsh.info](http://gmsh.info))
- **Python 3.x**: Scripting
- **NumPy**: Numerical operations
- **ParaView** (optional): Visualization

Install Python dependencies (recommended: venv):
```bash
python3 -m venv .venv
.venv/bin/pip install -r gmsh-learning/requirements.txt
```

Note: the Python `gmsh` package is optional and may not be available for all platforms.
This workflow uses the system `gmsh` binary (e.g., `gmsh -version`).

## Features

### Mesh Generation (workflow/generators)
- `simple_box.geo` / `box_hex.geo`: Structured hexahedral box meshes
- `cylinder_structured.geo` / `cylinder_hex.geo`: Cylinder meshes
- `glowinski_column.geo`: Glowinski column geometry
- Output in Gmsh MSH 4.2 format

### Format Conversion (workflow/converters/msh_to_vtk.py)
Converts Gmsh MSH 4.x files to:
- **VTK**: For visualization in ParaView
- **TRI**: For CFD solver input (DCORVG/KVERT format)

Features:
- Reads MSH 4.2 entity-based format
- Extracts hexahedral elements (type 5)
- Preserves node ordering for CFD compatibility

For VTK input (e.g. from the helix `.geo` scripts), `pe_partpy/tri2vtk_converter.py` converts VTK → TRI directly; this is what `run_geo_to_case.py` uses.

### Boundary Parametrization

Three methods for generating `.par` boundary files:

#### 1. Axis-Aligned (gen_par_from_tri.py)
```bash
python3 pe_partpy/gen_par_from_tri.py mesh.tri [--outdir OUT] [--tol 1e-6]
```
- Detects boundaries by comparing to axis planes (xmin, xmax, ymin, ymax, zmin, zmax)
- Works for axis-aligned box geometries
- Fast and reliable for simple cases
- Default output dir: `<tri_stem>/` next to the `.tri`

#### 2. Normal Clustering (gen_par_from_tri_by_normals.py)
```bash
python3 pe_partpy/gen_par_from_tri_by_normals.py mesh.tri [--outdir OUT] [--delta 30.0] [--btype Wall] [--min-faces N]
```
- Groups boundary faces by clustering face normals (max angle `--delta`)
- `--min-faces` merges small regions into neighbors
- Used as the default boundary step in `run_geo_to_case.py`

#### 3. Region-Growing (gen_par_from_tri_regions.py)
```bash
python3 pe_partpy/gen_par_from_tri_regions.py mesh.tri [--outdir OUT] [--angle 45.0]
```
- Grows regions where neighboring faces have similar normals (angle < threshold)
- Works for arbitrary geometries (cylinders, curved surfaces, etc.)
- Default output dir: `<tri_stem>_regions/` next to the `.tri`

All methods create a complete mesh folder with:
- `mesh.tri`: Hexahedral mesh
- `region_*.par` (or `xmin.par`, etc.): Boundary parametrizations
- `file.prj`: Project file listing all components

### Mesh Partitioning (pe_partpy)
Use for domain decomposition in parallel CFD:
```bash
python3 pe_partpy/PyPartitioner.py <NPart> <Strategy> <SubdivisionSpec> <Name> <file.prj>
```

Strategies are named (`metis_recursive`, `metis_vkway`, `metis_kway`, `axis_uniform`, `axis_cuts`, `plane_single`, `plane_dual`, `plane_ring`, plus `_reversed` METIS variants); legacy numeric codes are still accepted. The subdivision spec is a string such as `x3-y3-z3` or `x[0.2,0.5]-y[]-z[]`, or a plain integer for METIS sub-partitioning. Example:

```bash
python3 pe_partpy/PyPartitioner.py 27 axis_uniform x3-y3-z3 NEWFAC ./case/file.prj
```

Prefer `workflow/run_partition_to_vtu.py` to partition and get ParaView output in one step.

## Example Workflows

### Box Mesh
```bash
# Generate
gmsh workflow/generators/simple_box.geo -3 -o out/box.msh

# Convert
python3 workflow/converters/msh_to_vtk.py out/box.msh

# Boundaries (axis-aligned method)
python3 pe_partpy/gen_par_from_tri.py out/box.tri
```

### Cylinder Mesh
```bash
# Generate
gmsh workflow/generators/cylinder_structured.geo -3 -o out/cylinder.msh

# Convert
python3 workflow/converters/msh_to_vtk.py out/cylinder.msh

# Boundaries (region-growing method)
python3 pe_partpy/gen_par_from_tri_regions.py out/cylinder.tri --angle 45.0

# Visualize
python3 pe_partpy/tri2vtk_converter.py out/cylinder_regions/file.prj \
    -proj out/cylinder_regions
paraview out/cylinder_regions/main.vtu
```

### Helical Tube (ATC)
```bash
.venv/bin/python workflow/run_geo_to_case.py \
  gmsh-learning/examples/pure_quad_omesh_helix_minimal.geo \
  --outdir gmsh-learning/output/helix_case
python3 workflow/run_partition_to_vtu.py gmsh-learning/output/helix_case/file.prj 4 metis_recursive 1
```

## File Formats

### MSH 4.2 (Input)
Gmsh native format with entity-based sections:
- `$MeshFormat`: Version 4.2
- `$Nodes`: Node coordinates grouped by entity
- `$Elements`: Element connectivity grouped by entity

Read by `pe_partpy/mesh/mesh_io.py` (`readHexMeshFileMSH4`, `readNodesMSH4`, `readHexElementsMSH4`).

### VTK ASCII (Output)
ParaView visualization format:
- UNSTRUCTURED_GRID dataset
- Hexahedra as cell type 12

### TRI (Output)
CFD solver format with sections:
- Header: Element and node counts
- `DCORVG`: Vertex coordinates
- `KVERT`: Element connectivity (1-indexed)
- `KNPR`: Boundary markers

### PAR (Boundary)
Boundary parametrization format:
- Line 1: `<count> <type>` (e.g., "64 Wall")
- Line 2: Parameters (usually `''`; may carry an analytic descriptor, e.g. from ATC sphere fitting)
- Lines 3+: 1-based node indices

### PRJ (Project)
Simple list format:
- Line 1: Mesh filename (e.g., `mesh.tri`)
- Lines 2+: Boundary filenames (e.g., `region_0.par`)

## Contributing

This is a workflow integration project. To contribute:
1. Add new mesh generators to `workflow/generators/`
2. Enhance converters in `workflow/converters/`
3. Verify the end-to-end pipeline (`run_geo_to_case.py` + `run_partition_to_vtu.py`) still works

## License

See individual component repositories for license information.
