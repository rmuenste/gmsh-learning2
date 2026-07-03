# Gmsh to CFD Workflow

This workflow unifies mesh generation (gmsh-learning) and partitioning (pe_partpy) for CFD applications.

## Quick Start

1. Run setup check:
```bash
./setup.sh
```

2. Generate a hex mesh:
```bash
gmsh workflow/generators/simple_box.geo -3 -o out/box/mesh.msh
```

3. Convert to VTK and TRI formats:
```bash
python3 workflow/converters/msh_to_vtk.py out/box/mesh.msh
```

4. Inspect in ParaView:
```bash
paraview out/box/mesh.vtk
```

## One-shot .geo → case folder

```bash
.venv/bin/python workflow/run_geo_to_case.py gmsh-learning/examples/pure_quad_omesh_helix_minimal_bl1.geo
```

Custom output folder:
```bash
.venv/bin/python workflow/run_geo_to_case.py gmsh-learning/examples/pure_quad_omesh_helix_minimal_bl1.geo --outdir gmsh-learning/output/my_case
```

Parameterized run with Gmsh `-setnumber` overrides:
```bash
.venv/bin/python workflow/run_geo_to_case.py \
  gmsh-learning/examples/pure_quad_omesh_helix_minimal.geo \
  --setnumber start_angle_deg=45 \
  --setnumber end_angle_deg=90 \
  --setnumber nAxial=25 \
  --outdir gmsh-learning/output/atc_45deg_25layers_case
```

Parameterized ATC run with fitted spherical cap metadata for CFD:
```bash
.venv/bin/python workflow/run_geo_to_case.py \
  gmsh-learning/examples/pure_quad_omesh_helix_minimal.geo \
  --setnumber start_angle_deg=45 \
  --setnumber end_angle_deg=90 \
  --setnumber nAxial=25 \
  --fit-atc-spheres \
  --sphere-radius 10.0 \
  --sphere-free-dx-max 1.0 \
  --sphere-free-dy-max 1.0 \
  --sphere-free-dz-max 1.0 \
  --sphere-free-iters 32 \
  --outdir gmsh-learning/output/atc_45deg_25layers_case
```
This updates the second line of the two endpoint `region_####.par` files to `-3 <region_id>`
and writes `sphere_regions.json` with the fitted sphere centers, residual metrics, and fit settings.

### Periodic pipe mesh (`pipe_ogrid_z.geo`)

`workflow/generators/pipe_ogrid_z.geo` builds a z-axis pipe (R = 0.5, centered on (0,0))
with a true 5-block butterfly O-grid cross-section (48 cells/section, 8 across the diameter)
and a pure translational extrusion, so the z=0 and z=L end faces are exact translated copies.
ONELAB parameters: `L` (default 2.0) and `nLayers` (default 27; keep divisible by 27 for the
1×1×27 slab decomposition).

```bash
# primary mesh: L=2.0, 27 layers -> 1296 hexes, 1596 nodes
.venv/bin/python workflow/run_geo_to_case.py workflow/generators/pipe_ogrid_z.geo \
  --outdir cases/pipe_ogrid_z --tag-pipe-boundaries

# L=4.0 (8R) / 54-layer variant
.venv/bin/python workflow/run_geo_to_case.py workflow/generators/pipe_ogrid_z.geo \
  --setnumber L=4.0 --setnumber nLayers=54 \
  --outdir cases/pipe_ogrid_z_L4 --tag-pipe-boundaries

# partition smoke test: 27 clean z-slabs of 48 hexes each
.venv/bin/python workflow/run_partition_to_vtu.py cases/pipe_ogrid_z/file.prj 27 axis_uniform x1-y1-z27
```

`--tag-pipe-boundaries` runs `workflow/tag_pipe_boundaries.py` after boundary detection. It
classifies the three regions from node coordinates, verifies the end faces are congruent under
the (0,0,L) translation, then rewrites and renames the `.par` files:

- `hull.par`: `Wall` with the analytic cylinder descriptor `7 0d0 0d0 0d0 0.5d0 1d0 1d0 0d0`
  (type-7 parametrization: project x,y; z free)
- `zmin.par` / `zmax.par`: `Periodic` (non-BC tag; the CFD couples them by coordinate
  matching with `dPeriodicity(3) = L`), parameter `''`

The script is also runnable standalone: `tag_pipe_boundaries.py --case-dir cases/pipe_ogrid_z`.

### ATC sphere-fit behavior

The ATC workflow fits a fixed-radius sphere to the ring of nodes on each open helix end.
The first pass constrains the sphere center to the helix centerline. An optional second pass
then refines the center with free `dx/dy/dz` coordinate descent, controlled by:

- `--sphere-free-dx-max`
- `--sphere-free-dy-max`
- `--sphere-free-dz-max`
- `--sphere-free-iters`

For ATC end caps there are generally two geometric sphere branches that can match the same ring:
one that curves outward from the tube opening and one that curves inward into the helix. The workflow
now rejects the inward branch by comparing the fitted center against the boundary region normal and,
if necessary, reflecting the center across the cap plane onto the outward-curving side.

The resulting `sphere_regions.json` records:

- `center`: final sphere center used for the cap
- `rmse`, `residual_min`, `residual_max`: residual metrics for that final center
- `free_refined`: whether the free `dx/dy/dz` refinement ran
- `side_dot`: signed distance direction check against the cap normal
- `center_adjusted_for_outward_cap`: whether the center was moved to the outward branch

## Directory Structure

```
gmsh-learning2/
├── setup.sh                  # Subrepo setup + environment checker
├── workflow/
│   ├── README.md             # This file
│   ├── check_env.sh          # Environment check (gmsh, venv, deps)
│   ├── run_geo_to_case.py    # .geo → VTK → TRI → case folder pipeline
│   ├── run_partition_to_vtu.py  # Partition a case + generate VTUs
│   ├── parameterize_atc_sphere_caps.py  # ATC sphere-cap fitting
│   ├── generators/           # Gmsh .geo scripts
│   │   ├── simple_box.geo           # Structured hex box
│   │   ├── box_hex.geo              # Hex box variant
│   │   ├── cylinder_structured.geo  # O-grid cylinder
│   │   ├── cylinder_hex.geo         # Hex cylinder
│   │   ├── glowinski_column.geo     # Glowinski column geometry
│   │   └── pipe_ogrid_z.geo         # Periodic z-axis pipe (butterfly O-grid, saves VTK)
│   ├── tag_pipe_boundaries.py # Pipe boundary tagging (Wall hull + Periodic caps)
│   └── converters/           # Format conversion tools
│       └── msh_to_vtk.py    # MSH 4.x → VTK + TRI
├── _mesh/                    # Partitioning output (created at runtime)
├── gmsh-learning/            # Gmsh generation repo
└── pe_partpy/                # Partitioning & mesh I/O repo
```

## Components

### Mesh Generation

Create structured hexahedral meshes using Gmsh 4.x:
- `workflow/generators/*.geo`: box, cylinder, and Glowinski column templates (MSH 4.2 ASCII output)
- `gmsh-learning/examples/*.geo`: parametric helical O-meshes (save VTK directly, usable with `run_geo_to_case.py`)

### Format Conversion (msh_to_vtk.py)

Converts Gmsh MSH 4.x → VTK + TRI formats:
- **VTK**: For visualization in ParaView
- **TRI**: For CFD solver input

Features:
- Reads MSH 4.2 format with $Nodes and $Elements sections
- Extracts hexahedral elements (type 5)
- Preserves node ordering for CFD compatibility

### Mesh Partitioning (pe_partpy)

Use PyPartitioner.py for parallel CFD:
```bash
python3 pe_partpy/PyPartitioner.py <NPart> <Strategy> <SubdivisionSpec> <Name> <Project.prj>
```

Strategies are named (`metis_recursive`, `metis_vkway`, `metis_kway`, `axis_uniform`, `axis_cuts`, `plane_single`, `plane_dual`, `plane_ring`, plus `_reversed` METIS variants); legacy numeric codes (1, 2, 3, 11, 12, 13, -4, -5, -6, -7) are still accepted. The subdivision spec is a string such as `x3-y3-z3` or `x[0.2,0.5]-y[]-z[]`, or a plain integer for METIS sub-partitioning. Output goes to `_mesh/`.

### ParaView VTU From A Case Folder

If a case folder already contains `file.prj`, a `.tri` mesh, and `.par` boundary files, generate a ParaView-ready `.vtu` with:

```bash
python3 pe_partpy/tri2vtk_converter.py <case_dir>/file.prj -proj <case_dir>
```

Example:

```bash
python3 pe_partpy/tri2vtk_converter.py pe_partpy/3D_FAC_FBM/file.prj -proj pe_partpy/3D_FAC_FBM
```

This writes `main.vtu` into the case folder.

### Partition A Case And Generate VTU

If a case folder already exists and you want to partition it and immediately generate a ParaView file for inspection, use:

```bash
python3 workflow/run_partition_to_vtu.py <case_dir>/file.prj <n_part> <strategy> <subdivision_spec> [--mesh-name NAME]
```

Example:

```bash
python3 workflow/run_partition_to_vtu.py pe_partpy/3D_FAC_FBM/file.prj 4 axis_cuts 'x@[0.58333333,1.05,1.7]-y[]-z[]' --mesh-name 3D_FAC_FBM_axis_cuts
```

This runs `PyPartitioner.py`, writes the partitioned case into `_mesh/<mesh-name>/`, and then creates:

```bash
_mesh/<mesh-name>/main.vtu
```

It also writes one `.vtu` per subpartition, for example:

```bash
_mesh/<mesh-name>/sub0001/GRID0001.vtu
_mesh/<mesh-name>/sub0002/GRID0001.vtu
```

and a ParaView collection file:

```bash
_mesh/<mesh-name>/subdomains.pvd
```

Use `--skip-subdomain-vtu` if you only want the combined `main.vtu`.

### Which Converter To Use

Use `workflow/converters/msh_to_vtk.py` when the starting point is a raw Gmsh `.msh` file:

```bash
python3 workflow/converters/msh_to_vtk.py input.msh [output_basename]
```

This writes:

```bash
output_basename.vtk
output_basename.tri
```

Use `pe_partpy/tri2vtk_converter.py` when the starting point is already a mesh case folder with `file.prj`, `.tri`, and `.par` files:

```bash
python3 pe_partpy/tri2vtk_converter.py <case_dir>/file.prj -proj <case_dir>
```

This writes:

```bash
<case_dir>/main.vtu
```

## File Formats

### MSH 4.2 (Input)
Gmsh native format with structured sections:
- `$MeshFormat`: Version info
- `$Nodes`: Node coordinates grouped by entity
- `$Elements`: Element connectivity grouped by entity

### VTK ASCII (Output)
ParaView-compatible visualization format:
- UNSTRUCTURED_GRID dataset
- Hexahedra as cell type 12

### TRI (Output)
Custom CFD solver format:
- DCORVG: Vertex coordinates
- KVERT: Element connectivity (1-indexed)
- KNPR: Boundary markers

## Requirements

- Gmsh 4.x
- Python 3.x
- numpy

## Boundary Parametrization (.par files)

Three generators in `pe_partpy/`, all writing `region_*.par` + `file.prj` + a `.tri` copy into `--outdir`:

```bash
# Axis-aligned (boxes)
python3 pe_partpy/gen_par_from_tri.py mesh.tri [--outdir OUT] [--tol 1e-6]

# Normal clustering (general geometries; default in run_geo_to_case.py)
python3 pe_partpy/gen_par_from_tri_by_normals.py mesh.tri [--outdir OUT] [--delta 30.0] [--min-faces N]

# Region-growing (curved surfaces)
python3 pe_partpy/gen_par_from_tri_regions.py mesh.tri [--outdir OUT] [--angle 45.0]
```

## Testing

Quick end-to-end smoke test:
```bash
.venv/bin/python workflow/run_geo_to_case.py gmsh-learning/examples/pure_quad_omesh_helix_minimal.geo --outdir out/helix_case
python3 workflow/run_partition_to_vtu.py out/helix_case/file.prj 4 metis_recursive 1
paraview _mesh/*/main.vtu
```
