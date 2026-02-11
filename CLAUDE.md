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
├── README.md                      # Comprehensive workflow documentation
├── CLAUDE.md                      # This file - integration guidance
├── MODIFICATIONS.md               # Changes made to subrepos
├── setup.sh                       # Environment setup checker
├── .gitignore                     # Git ignore patterns
│
├── workflow/                      # Unified workflow scripts (NEW)
│   ├── README.md                 # Detailed workflow documentation
│   ├── generators/               # Gmsh .geo mesh generation scripts
│   │   ├── simple_box.geo       # Structured hex box (working)
│   │   ├── cylinder_structured.geo  # O-grid cylinder
│   │   └── ...                   # Other geometry templates
│   └── converters/               # Format conversion utilities
│       └── msh_to_vtk.py         # MSH 4.x → VTK + TRI converter
│
├── tests/                         # Test cases and outputs
│   └── test_cylinder/            # Example test data
│
├── patches/                       # Patch files for subrepo modifications
│
├── gmsh-learning/                 # Subrepo: Helical mesh generation
│   ├── CLAUDE.md                 # Gmsh-specific guidance
│   ├── examples/                 # Working .geo scripts
│   │   ├── pure_quad_omesh_helix_minimal.geo  # Baseline working
│   │   └── ...
│   └── ...                       # See gmsh-learning/CLAUDE.md
│
└── pe_partpy/                     # Subrepo: Mesh partitioning
    ├── CLAUDE.md                 # Partitioner-specific guidance
    ├── PyPartitioner.py          # Main partitioning entry point
    ├── mesh/                     # Mesh data structures
    │   ├── mesh.py              # Quad/Hex mesh classes
    │   └── mesh_io.py           # I/O operations (MODIFIED)
    ├── partitioner/              # Partitioning algorithms
    │   └── part.py              # METIS integration
    ├── gen_par_from_tri.py      # Axis-aligned boundary detection
    ├── gen_par_from_tri_by_normals.py  # Normal-based detection
    ├── gen_par_from_tri_regions.py     # Region-growing (NEW)
    ├── tri2vtk_converter.py     # Visualization converter
    └── ...                       # See pe_partpy/CLAUDE.md
```

## Complete Workflow Pipeline

### Step-by-Step Process

```
1. Mesh Generation (Gmsh)
   ↓
2. Format Conversion (MSH 4.x → VTK + TRI)
   ↓
3. Boundary Parametrization (.par files)
   ↓
4. [Optional] Mesh Partitioning (METIS)
   ↓
5. Visualization/CFD Solver Input
```

### Detailed Commands

#### 1. Generate Mesh (Gmsh)

**Simple box geometry:**
```bash
cd workflow/generators
gmsh simple_box.geo -3 -o ../../tests/my_box/mesh.msh
```

**O-grid cylinder:**
```bash
cd workflow/generators
gmsh cylinder_structured.geo -3 -o ../../tests/my_cylinder/mesh.msh
```

**Helical tube (ATC):**
```bash
cd gmsh-learning/examples
gmsh pure_quad_omesh_helix_minimal.geo -3 -o ../../tests/helix/mesh.msh
```

#### 2. Convert to VTK + TRI Format

```bash
python3 workflow/converters/msh_to_vtk.py tests/my_mesh/mesh.msh
```

**Output:**
- `mesh.vtk` - ParaView visualization
- `mesh.tri` - CFD solver format (DCORVG/KVERT)

#### 3. Generate Boundary Parametrization

**Method A: Axis-aligned (for boxes):**
```bash
python3 pe_partpy/gen_par_from_tri.py tests/my_mesh/mesh.tri --outdir tests/my_mesh/mesh_regions
```

**Method B: Region-growing (for any geometry):**
```bash
python3 pe_partpy/gen_par_from_tri_regions.py tests/my_mesh/mesh.tri --outdir tests/my_mesh/mesh_regions --angle 45.0
```

**Output:**
- `mesh_regions/mesh.tri` - Copy of mesh file
- `mesh_regions/region_0.par` - Boundary parametrizations
- `mesh_regions/file.prj` - Project file listing all components

#### 4. Visualize

```bash
python3 pe_partpy/tri2vtk_converter.py tests/my_mesh/mesh_regions/file.prj -proj tests/my_mesh/mesh_regions
paraview tests/my_mesh/mesh_regions/main.vtu
```

#### 5. Partition (Optional - for parallel CFD)

```bash
cd pe_partpy
python3 PyPartitioner.py <NPart> <Method> <NSubPart> <Name> ../tests/my_mesh/mesh_regions/file.prj
```

**Example:**
```bash
python3 PyPartitioner.py 8 1 1 PART ../tests/my_mesh/mesh_regions/file.prj
```

## Key File Formats

### MSH 4.2 (Gmsh Output)
- Entity-based format with separate node/element sections
- Supported element types: Hex8 (type 5), Hex27 (type 92)
- **New support added** via `pe_partpy/mesh/mesh_io.py` modifications

### VTK ASCII (Visualization)
- UNSTRUCTURED_GRID format
- Hexahedra as cell type 12
- For ParaView visualization

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
- **Key scripts**: `examples/pure_quad_omesh_helix_minimal.geo` (working baseline)
- **See**: `gmsh-learning/CLAUDE.md` for detailed Gmsh guidance

### pe_partpy
- **Focus**: Mesh partitioning with METIS
- **Methods**: Recursive (1), VKway (2), Kway (3), Axis-based (-3, -4, -6), Ring (6)
- **Modifications**: Added MSH 4.x support, region-growing boundary detection
- **See**: `pe_partpy/CLAUDE.md` for detailed partitioning guidance

## Modifications to External Repos

This integration required modifications to `pe_partpy` (see `MODIFICATIONS.md`):

### 1. New File: `gen_par_from_tri_regions.py`
- Region-growing algorithm for boundary detection
- Works on arbitrary geometries (curved surfaces, cylinders)
- Configurable angular threshold (default: 45°)

### 2. Modified: `mesh/mesh_io.py`
- Added `readHexMeshFileMSH4()` - Main MSH 4.x reader
- Added `readNodesMSH4()` - Entity-based node parsing
- Added `readHexElementsMSH4()` - Hexahedral element extraction
- **Location**: Insert before `readNodes()` function (~line 655)

**Note**: `gmsh-learning` is used as-is without modifications.

## Development Workflow

### Adding New Geometries

1. Create `.geo` file in `workflow/generators/`
2. Test mesh generation: `gmsh mygeom.geo -3 -o test.msh`
3. Verify MSH 4.x format compatibility
4. Document in workflow README

### Testing New Conversions

1. Generate test mesh in `tests/test_name/`
2. Run converter: `python3 workflow/converters/msh_to_vtk.py tests/test_name/mesh.msh`
3. Verify VTK output in ParaView
4. Test boundary detection with both methods (axis-aligned and region-growing)
5. Verify `.prj` file completeness

### Debugging Partitioning

1. Check mesh quality: `python3 pe_partpy/mesh/mesh.py` (if has quality functions)
2. Verify `.tri` format correctness (1-based indexing, correct element count)
3. Test with simple METIS method first (method 1)
4. Check partition balance in terminal output

## Common Tasks

### "I want to mesh a box and partition it"
```bash
# 1. Generate
gmsh workflow/generators/simple_box.geo -3 -o tests/box/mesh.msh

# 2. Convert
python3 workflow/converters/msh_to_vtk.py tests/box/mesh.msh

# 3. Boundaries (axis-aligned is best for boxes)
python3 pe_partpy/gen_par_from_tri.py tests/box/mesh.tri --outdir tests/box/regions

# 4. Partition into 8 parts
cd pe_partpy
python3 PyPartitioner.py 8 1 1 BOX ../tests/box/regions/file.prj
```

### "I want to mesh a cylinder"
```bash
# 1. Generate
gmsh workflow/generators/cylinder_structured.geo -3 -o tests/cyl/mesh.msh

# 2. Convert
python3 workflow/converters/msh_to_vtk.py tests/cyl/mesh.msh

# 3. Boundaries (region-growing for curved surfaces)
python3 pe_partpy/gen_par_from_tri_regions.py tests/cyl/mesh.tri --outdir tests/cyl/regions --angle 45.0

# 4. Visualize
python3 pe_partpy/tri2vtk_converter.py tests/cyl/regions/file.prj -proj tests/cyl/regions
paraview tests/cyl/regions/main.vtu
```

### "I want to mesh a helical tube (ATC)"
```bash
# 1. Generate from gmsh-learning examples
cd gmsh-learning/examples
gmsh pure_quad_omesh_helix_minimal.geo -3 -o ../../tests/helix/mesh.msh

# 2. Convert
cd ../..
python3 workflow/converters/msh_to_vtk.py tests/helix/mesh.msh

# 3. Boundaries (region-growing for helical geometry)
python3 pe_partpy/gen_par_from_tri_regions.py tests/helix/mesh.tri --outdir tests/helix/regions --angle 30.0
```

## Dependencies

- **Gmsh 4.x**: Mesh generation ([gmsh.info](http://gmsh.info))
- **Python 3.x**: Scripting and automation
- **NumPy**: Numerical operations
- **METIS**: Graph partitioning library (libmetis.so in pe_partpy/partitioner/)
- **ParaView** (optional): Visualization

**Install Python dependencies:**
```bash
pip3 install numpy
```

**Verify setup:**
```bash
./setup.sh
```

## Git Structure

This is a **parent repo** with two independent git subrepos:
- Parent: `gmsh-learning2` (1 commit)
- Subrepo: `gmsh-learning` (~12 commits, helical meshes)
- Subrepo: `pe_partpy` (~24 commits, partitioning tools)

Each subrepo has its own git history and can be updated independently. Use standard git commands within each directory.

## Testing Status

**Verified working:**
- Simple box mesh (64 hex elements, 6 boundaries)
- O-grid cylinder (384 hex elements, 7 boundaries)
- Helical tube (48 hex elements with ultra-coarse settings)
- MSH 4.x format conversion
- Region-growing boundary detection
- Axis-aligned boundary detection

## Recent Development Activity

**pe_partpy** (current directory):
- Cube-to-case folder automation
- Boundary identification by normals
- VTK parsing improvements
- Ring-based partitioning methods
- Code modernization

**gmsh-learning**:
- O-mesh with boundary layers
- Sphere fitting scripts
- Gmsh wrapper scripts
- Documentation improvements

**Integration** (gmsh-learning2):
- Unified workflow scripts
- MSH 4.x converter
- Cross-repo documentation

## When Working with This Repo

1. **Respect subrepo boundaries**: Each subrepo has its own CLAUDE.md
2. **Document modifications**: Update MODIFICATIONS.md if changing subrepo code
3. **Test full pipeline**: After changes, verify end-to-end workflow
4. **Use existing patterns**: Follow established file naming and directory structure
5. **Check both README.md and CLAUDE.md**: README for users, CLAUDE.md for development

## Key Contacts / References

- Gmsh documentation: http://gmsh.info/doc/texinfo/gmsh.html
- METIS documentation: http://glaros.dtc.umn.edu/gkhome/metis/metis/overview
- VTK file format: https://vtk.org/wp-content/uploads/2015/04/file-formats.pdf

## Version Information

- **Created**: 2026-02-11
- **Gmsh Version**: 4.12.1 (tested)
- **Python Version**: 3.x
- **METIS**: Integrated via libmetis.so

---

For detailed component-specific guidance:
- See `gmsh-learning/CLAUDE.md` for helical mesh generation
- See `pe_partpy/CLAUDE.md` for mesh partitioning details
- See `README.md` for user-facing workflow documentation
- See `MODIFICATIONS.md` for subrepo change tracking
