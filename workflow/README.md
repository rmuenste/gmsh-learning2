# Gmsh to CFD Workflow

This workflow unifies mesh generation (gmsh-learning) and partitioning (pe_partpy) for CFD applications.

## Quick Start

1. Run setup check:
```bash
./setup.sh
```

2. Generate a hex mesh:
```bash
cd workflow/generators
gmsh simple_box.geo -3 -o ../../tests/test_cylinder/mesh.msh
```

3. Convert to VTK and TRI formats:
```bash
python3 workflow/converters/msh_to_vtk.py tests/test_cylinder/mesh.msh
```

4. Inspect in ParaView:
```bash
paraview tests/test_cylinder/mesh.vtk
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
├── setup.sh                  # Setup verification script
├── workflow/
│   ├── generators/           # Gmsh .geo scripts
│   │   ├── simple_box.geo   # Working structured hex box
│   │   └── cylinder_hex.geo # (WIP) Hex cylinder attempt
│   ├── converters/           # Format conversion tools
│   │   └── msh_to_vtk.py    # MSH 4.x → VTK + TRI
│   └── README.md             # This file
├── tests/
│   └── test_cylinder/        # Test outputs
├── gmsh-learning/            # Gmsh generation repo
└── pe_partpy/                # Partitioning & mesh I/O repo
```

## Components

### Mesh Generation (gmsh-learning)

Create structured hexahedral meshes using Gmsh 4.x:
- `simple_box.geo`: Reliable structured hex box mesh
- Output: MSH 4.2 format (ASCII)

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
python pe_partpy/PyPartitioner.py <NPart> <Method> <NSubPart> <Name> <Project.prj>
```

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

## Testing

The test case `simple_box` demonstrates the complete workflow:
- Input: 2×1×1 box with 64 hexahedra (4×4×4 divisions)
- Output: 125 nodes, 64 hex elements
- Verified to load correctly in ParaView

## Next Steps

- Create cylindrical hex mesh generator (cylinder_hex.geo needs fixing)
- Add boundary condition (.par) file generation
- Integrate with PyPartitioner for domain decomposition
- Add helical mesh support from gmsh-learning
