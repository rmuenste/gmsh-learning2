# CLAUDE.md - Gmsh to CFD Workflow Integration

This file provides guidance to Claude Code when working with this integrated mesh generation repository.

## Project Overview

**gmsh-learning2** is a unified workflow repository that integrates two specialized mesh generation tools for CFD applications:

1. **gmsh-learning**: Helical O-mesh generation using Gmsh
2. **pe_partpy**: Mesh partitioning and I/O for parallel CFD

The parent repository provides integration scripts, format converters, and a unified pipeline from mesh generation to CFD-ready partitioned meshes.

## Repository Structure

```
gmsh-learning2/                    # Parent integration repo (this level)
├── README.md                      # Workflow documentation (user-facing)
├── CLAUDE.md                      # This file - integration guidance
├── setup.sh                       # Clones/updates the two subrepos, checks environment
├── .gitignore                     # Git ignore patterns
│
├── workflow/                      # Unified workflow scripts
│   ├── README.md                 # Detailed workflow documentation
│   ├── check_env.sh              # Environment check (gmsh, venv, Python deps)
│   ├── run_geo_to_case.py        # Automated .geo → VTK → TRI → case folder pipeline
│   ├── run_partition_to_vtu.py   # PyPartitioner run + VTU generation for ParaView
│   ├── parameterize_atc_sphere_caps.py  # Fit spheres to ATC helix end caps, annotate .par files
│   ├── generators/               # Gmsh .geo mesh generation scripts
│   │   ├── simple_box.geo       # Structured hex box
│   │   ├── box_hex.geo          # Hex box variant
│   │   ├── cylinder_structured.geo  # O-grid cylinder
│   │   ├── cylinder_hex.geo     # Hex cylinder
│   │   └── glowinski_column.geo # Glowinski column geometry
│   └── converters/               # Format conversion utilities
│       └── msh_to_vtk.py         # MSH 4.x → VTK + TRI converter
│
├── _mesh/                         # Partitioning output (created at runtime, gitignored)
│
├── gmsh-learning/                 # Subrepo: Helical mesh generation
│   ├── CLAUDE.md                 # Gmsh-specific guidance
│   ├── examples/
│   │   ├── pure_quad_omesh_helix_minimal.geo      # Baseline working (saves VTK)
│   │   ├── pure_quad_omesh_helix_minimal_bl1.geo  # With boundary layer (saves VTK)
│   │   └── pure_quad_omesh_helix_with_caps.geo    # With end caps
│   └── ...                       # See gmsh-learning/CLAUDE.md
│
└── pe_partpy/                     # Subrepo: Mesh partitioning
    ├── CLAUDE.md                 # Partitioner-specific guidance
    ├── PyPartitioner.py          # Main partitioning entry point
    ├── mesh/                     # Mesh data structures
    │   ├── mesh.py              # Quad/Hex mesh classes
    │   └── mesh_io.py           # I/O operations (includes MSH 4.x readers)
    ├── partitioner/              # Partitioning algorithms (METIS via libmetis.so)
    ├── gen_par_from_tri.py      # Axis-aligned boundary detection (boxes)
    ├── gen_par_from_tri_by_normals.py  # Normal-clustering boundary detection (default in pipeline)
    ├── gen_par_from_tri_regions.py     # Region-growing boundary detection
    ├── tri2vtk_converter.py     # VTK ↔ TRI conversion + VTU visualization
    └── ...                       # See pe_partpy/CLAUDE.md
```

## Workflow Pipelines

There are two ways to go from geometry to a CFD-ready case: the automated runner scripts (preferred) and the manual step-by-step path.

### A. Automated pipeline (preferred)

**Step 1: `.geo` → case folder** with `workflow/run_geo_to_case.py`:

```bash
python3 workflow/run_geo_to_case.py gmsh-learning/examples/pure_quad_omesh_helix_minimal.geo --outdir cases/helix
```

Pipeline stages: run gmsh (`-3`) → locate the VTK output → convert VTK → TRI (via `tri2vtk_converter.py`) → generate boundary `.par` files + `file.prj` (via `gen_par_from_tri_by_normals.py`).

Requirements and options:
- The `.geo` file must contain a `Save "...vtk";` statement (the helix examples do; override the expected path with `--vtk`). The `workflow/generators/*.geo` scripts save MSH instead — use the manual pipeline (B) for those.
- `--setnumber name=value` (repeatable) passes ONELAB parameter overrides to gmsh; the VTK/case output gets a derived suffix so parameterized runs don't collide.
- `--gmsh` / `--gmsh-args` override the gmsh executable and extra CLI args.
- `--fit-atc-spheres` fits fixed-radius spheres to the two open ATC helix ends and annotates the matching `.par` files (needs `R`, `Pturn`, `start_angle_deg`, `end_angle_deg` in the `.geo` or via `--setnumber`). Related knobs: `--sphere-radius` (default 10.0), `--sphere-free-{dx,dy,dz}-max`, `--sphere-free-iters`. The underlying tool is `workflow/parameterize_atc_sphere_caps.py`, which can also be run standalone.

**Step 2: partition + visualize** with `workflow/run_partition_to_vtu.py`:

```bash
python3 workflow/run_partition_to_vtu.py cases/helix/file.prj 27 axis_uniform x3-y3-z3
```

Runs `PyPartitioner.py`, writes output under `_mesh/<mesh-name>/`, and generates `main.vtu` (plus per-subpartition VTUs unless `--skip-subdomain-vtu`) for ParaView. `--mesh-name` overrides the derived output name; `--format` is passed through to PyPartitioner (default `v2`).

### B. Manual step-by-step pipeline

```
1. Mesh generation (Gmsh, MSH 4.2 output)
   ↓
2. Format conversion (MSH 4.x → VTK + TRI)
   ↓
3. Boundary parametrization (.par files + file.prj)
   ↓
4. [Optional] Mesh partitioning (METIS)
   ↓
5. Visualization / CFD solver input
```

#### 1. Generate mesh (Gmsh)

```bash
gmsh workflow/generators/simple_box.geo -3 -o out/box/mesh.msh
gmsh workflow/generators/cylinder_structured.geo -3 -o out/cyl/mesh.msh
```

#### 2. Convert to VTK + TRI

```bash
python3 workflow/converters/msh_to_vtk.py out/box/mesh.msh [output_basename]
```

Output: `mesh.vtk` (ParaView) and `mesh.tri` (CFD solver format).

Note: `pe_partpy/tri2vtk_converter.py` also converts VTK → TRI directly (`tri2vtk_converter.py input.vtk output.tri`) — that is what the automated pipeline uses.

#### 3. Generate boundary parametrization

Three methods, all writing `region_*.par` + `file.prj` + a copy of the `.tri` into `--outdir`:

```bash
# Axis-aligned (boxes; also has --tol)
python3 pe_partpy/gen_par_from_tri.py out/box/mesh.tri --outdir out/box/regions

# Normal clustering (general geometries; used by the automated pipeline)
python3 pe_partpy/gen_par_from_tri_by_normals.py out/cyl/mesh.tri --outdir out/cyl/regions --delta 30.0
#   also: --btype Wall, --parameter "''", --min-faces N (merge small regions)

# Region-growing (curved surfaces)
python3 pe_partpy/gen_par_from_tri_regions.py out/cyl/mesh.tri --outdir out/cyl/regions --angle 45.0
```

#### 4. Visualize

```bash
python3 pe_partpy/tri2vtk_converter.py out/cyl/regions/file.prj -proj out/cyl/regions
paraview out/cyl/regions/main.vtu
```

#### 5. Partition (optional, for parallel CFD)

```bash
cd pe_partpy
python3 PyPartitioner.py <NPart> <Strategy> <SubdivisionSpec> <Name> <project.prj> [-f/--format v2]
```

Output goes to `_mesh/` (created next to the working directory).

## PyPartitioner Strategies

Strategies are passed **by name**; legacy numeric codes are still accepted:

| Strategy | Legacy code | Notes |
|---|---|---|
| `metis_recursive` | 1 | METIS recursive bisection |
| `metis_vkway` | 2 | METIS VKway |
| `metis_kway` | 3 | METIS Kway |
| `metis_recursive_reversed` | 11 | |
| `metis_vkway_reversed` | 12 | |
| `metis_kway_reversed` | 13 | |
| `axis_uniform` | -4 | Uniform axis-aligned slabs |
| `axis_cuts` | — | Explicit cut positions |
| `plane_single` | -5 | |
| `plane_dual` | -6 | |
| `plane_ring` | -7 | Ring-based partitioning |

The subdivision spec is a string, e.g. `x3-y3-z3` (uniform 3×3×3), `x[0.2,0.5]-y[]-z[]` (explicit cuts), or a plain integer for METIS sub-partitioning.

Examples:
```bash
python3 PyPartitioner.py 27 axis_uniform x3-y3-z3 NEWFAC ./dev3x3x3/dev3x3x3.prj
python3 PyPartitioner.py 3 axis_cuts x[0.2,0.5]-y[]-z[] NEWFAC ./box/file.prj
python3 PyPartitioner.py 8 metis_recursive 1 PART ./regions/file.prj   # or legacy: 8 1 1 PART ...
```

## Key File Formats

### MSH 4.2 (Gmsh Output)
- Entity-based format with separate node/element sections
- Supported element types: Hex8 (type 5), Hex27 (type 92)
- Read by `pe_partpy/mesh/mesh_io.py` (`readHexMeshFileMSH4`, `readNodesMSH4`, `readHexElementsMSH4`)

### VTK ASCII (Visualization)
- UNSTRUCTURED_GRID format, hexahedra as cell type 12
- For ParaView; also the intermediate format in the automated pipeline

### TRI (CFD Input)
- Custom format with DCORVG (vertices) and KVERT (connectivity) sections
- 1-based indexing
- Header: element count, node count, boundary markers

### PAR (Boundary Definition)
```
<node_count> <boundary_type>
''
<node_id_1>
<node_id_2>
...
```
Wall regions can carry an analytic parametrization line instead of `''` (e.g. a sphere descriptor written by `parameterize_atc_sphere_caps.py`).

### PRJ (Project File)
```
mesh.tri
region_0.par
region_1.par
...
```

## Subrepo-Specific Details

### gmsh-learning
- **Focus**: Parametric helical O-mesh generation
- **Status**: Tested with Gmsh 4.12
- **Key scripts**: `examples/pure_quad_omesh_helix_minimal.geo` (working baseline, saves VTK directly)
- **See**: `gmsh-learning/CLAUDE.md` for detailed Gmsh guidance

### pe_partpy
- **Focus**: Mesh partitioning with METIS (named strategies, see table above)
- **MSH 4.x support**: `mesh/mesh_io.py` provides `readHexMeshFileMSH4` (~line 655), `readNodesMSH4`, `readHexElementsMSH4`
- **Boundary detection**: three generators (`gen_par_from_tri.py`, `gen_par_from_tri_by_normals.py`, `gen_par_from_tri_regions.py`)
- **See**: `pe_partpy/CLAUDE.md` for detailed partitioning guidance

## Development Workflow

### Adding New Geometries

1. Create `.geo` file in `workflow/generators/`
2. Test mesh generation: `gmsh mygeom.geo -3 -o test.msh` (or add a `Save "...vtk";` line to make it usable with `run_geo_to_case.py`)
3. Verify format compatibility (MSH 4.2 or VTK)
4. Document in `workflow/README.md`

### Testing New Conversions

1. Generate a test mesh
2. Run the converter (`msh_to_vtk.py` for MSH input, `tri2vtk_converter.py` for VTK input)
3. Verify VTK output in ParaView
4. Test boundary detection (by-normals is the pipeline default; axis-aligned for boxes; region-growing as alternative)
5. Verify `file.prj` completeness

### Debugging Partitioning

1. Verify `.tri` format correctness (1-based indexing, correct element count)
2. Test with `metis_recursive` first
3. Check partition balance in terminal output
4. Inspect `_mesh/<name>/main.vtu` in ParaView (`run_partition_to_vtu.py` generates it)

## Dependencies

- **Gmsh 4.x**: Mesh generation ([gmsh.info](http://gmsh.info))
- **Python 3.x** + **NumPy**
- **METIS**: Graph partitioning (bundled as `pe_partpy/partitioner/libmetis.so`)
- **ParaView** (optional): Visualization

**Verify setup:**
```bash
./setup.sh              # clones/updates subrepos, checks environment
workflow/check_env.sh   # checks gmsh, .venv, Python deps
```

## Git Structure

This is a **parent repo** with two independent git subrepos (each has its own history; `setup.sh` clones them if missing):
- Parent: `gmsh-learning2`
- Subrepo: `gmsh-learning` (helical meshes)
- Subrepo: `pe_partpy` (partitioning tools)

Use standard git commands within each directory. Note: `gmsh-learning/` and `pe_partpy/` are untracked in the parent repo (nested repos, not submodules).

## When Working with This Repo

1. **Respect subrepo boundaries**: Each subrepo has its own CLAUDE.md
2. **Test full pipeline**: After changes, verify end-to-end workflow (ideally via `run_geo_to_case.py` + `run_partition_to_vtu.py`)
3. **Use existing patterns**: Follow established file naming and directory structure
4. **Check both README.md and CLAUDE.md**: README for users, CLAUDE.md for development

## Key Contacts / References

- Gmsh documentation: http://gmsh.info/doc/texinfo/gmsh.html
- METIS documentation: http://glaros.dtc.umn.edu/gkhome/metis/metis/overview
- VTK file format: https://vtk.org/wp-content/uploads/2015/04/file-formats.pdf

## Version Information

- **Created**: 2026-02-11, **last verified against code**: 2026-07-03
- **Gmsh Version**: 4.12.1 (tested)
- **Python Version**: 3.x
- **METIS**: Integrated via libmetis.so

---

For detailed component-specific guidance:
- See `gmsh-learning/CLAUDE.md` for helical mesh generation
- See `pe_partpy/CLAUDE.md` for mesh partitioning details
- See `README.md` for user-facing workflow documentation
