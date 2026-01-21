# Gmsh to CFD Workflow

Unified workflow for generating, converting, and preparing hexahedral meshes for CFD applications.

## Overview

This project integrates:
- **gmsh-learning**: Gmsh scripts for helical and structured hex mesh generation
- **pe_partpy**: Python tools for mesh partitioning and I/O
- **workflow**: New driver scripts unifying the mesh generation pipeline

## Quick Start

```bash
# 1. Run setup check
./setup.sh

# 2. Generate a mesh (example: structured box)
cd workflow/generators
gmsh simple_box.geo -3 -o ../../tests/test_cylinder/my_mesh.msh

# 3. Convert to VTK and TRI formats
python3 workflow/converters/msh_to_vtk.py tests/test_cylinder/my_mesh.msh

# 4. Generate boundary parametrization
python3 pe_partpy/gen_par_from_tri_regions.py tests/test_cylinder/my_mesh.tri

# 5. Visualize in ParaView
python3 pe_partpy/tri2vtk_converter.py tests/test_cylinder/my_mesh_regions/file.prj \
    -proj tests/test_cylinder/my_mesh_regions
paraview tests/test_cylinder/my_mesh_regions/main.vtu
```

## Project Structure

```
gmsh-learning2/
├── README.md                 # This file
├── setup.sh                  # Environment setup checker
├── .gitignore               # Git ignore patterns
│
├── workflow/                 # NEW: Unified workflow scripts
│   ├── README.md            # Detailed workflow documentation
│   ├── generators/          # Gmsh .geo mesh generation scripts
│   │   ├── simple_box.geo           # Structured hex box (working)
│   │   ├── cylinder_structured.geo  # O-grid cylinder with hole
│   │   └── ...
│   └── converters/          # Format conversion utilities
│       └── msh_to_vtk.py    # MSH 4.x → VTK + TRI converter
│
├── tests/                    # Test cases and outputs
│   └── test_cylinder/       # Example test outputs
│
├── gmsh-learning/           # Separate git repo: Helical mesh generation
│   └── (external repo)
│
└── pe_partpy/               # Separate git repo: Mesh partitioning
    ├── (external repo files)
    ├── mesh/mesh_io.py              # MODIFIED: Added readHexMeshFileMSH4()
    └── gen_par_from_tri_regions.py  # NEW: Region-growing boundary detection
```

## Dependencies

- **Gmsh 4.x**: Mesh generation ([gmsh.info](http://gmsh.info))
- **Python 3.x**: Scripting
- **NumPy**: Numerical operations
- **ParaView** (optional): Visualization

Install Python dependencies:
```bash
pip3 install numpy
```

## Features

### Mesh Generation (workflow/generators)
- `simple_box.geo`: Structured hexahedral box mesh
- `cylinder_structured.geo`: O-grid cylinder with central hole
- Support for Gmsh MSH 4.2 format

### Format Conversion (workflow/converters/msh_to_vtk.py)
Converts Gmsh MSH 4.x files to:
- **VTK**: For visualization in ParaView
- **TRI**: For CFD solver input (DCORVG/KVERT format)

Features:
- Reads MSH 4.2 entity-based format
- Extracts hexahedral elements (type 5)
- Preserves node ordering for CFD compatibility

### Boundary Parametrization

Two methods for generating `.par` boundary files:

#### 1. Axis-Aligned (gen_par_from_tri.py)
```bash
python3 pe_partpy/gen_par_from_tri.py mesh.tri [--outdir OUT] [--tol 1e-6]
```
- Detects boundaries by comparing to axis planes (xmin, xmax, ymin, ymax, zmin, zmax)
- Works for axis-aligned box geometries
- Fast and reliable for simple cases

#### 2. Region-Growing (gen_par_from_tri_regions.py) - NEW
```bash
python3 pe_partpy/gen_par_from_tri_regions.py mesh.tri [--outdir OUT] [--angle 45.0]
```
- Detects boundaries by analyzing face normal angles
- Groups faces into regions where neighbors have similar normals (angle < threshold)
- Works for arbitrary geometries (cylinders, curved surfaces, etc.)
- More general and flexible

Both methods create a complete mesh folder with:
- `mesh.tri`: Hexahedral mesh
- `region_*.par` or `xmin.par`, etc.: Boundary parametrizations
- `file.prj`: Project file listing all components

### Mesh Partitioning (pe_partpy)
Use for domain decomposition in parallel CFD:
```bash
python3 pe_partpy/PyPartitioner.py <NPart> <Method> <NSubPart> <Name> <file.prj>
```

## Modifications to External Repos

### pe_partpy Modifications:

1. **mesh/mesh_io.py**: Added MSH 4.x support
   - `readHexMeshFileMSH4()`: Read Gmsh MSH 4.2 format
   - `readNodesMSH4()`: Parse entity-based node blocks
   - `readHexElementsMSH4()`: Extract hexahedral elements

2. **gen_par_from_tri_regions.py**: NEW script
   - Region-growing algorithm for boundary detection
   - Face normal analysis with angular threshold
   - Handles arbitrary mesh geometries

### gmsh-learning:
- No modifications, used as-is for helical mesh generation

## Example Workflows

### Box Mesh
```bash
# Generate
gmsh workflow/generators/simple_box.geo -3 -o tests/box.msh

# Convert
python3 workflow/converters/msh_to_vtk.py tests/box.msh

# Boundaries (axis-aligned method)
python3 pe_partpy/gen_par_from_tri.py tests/box.tri
```

### Cylinder Mesh
```bash
# Generate
gmsh workflow/generators/cylinder_structured.geo -3 -o tests/cylinder.msh

# Convert
python3 workflow/converters/msh_to_vtk.py tests/cylinder.msh

# Boundaries (region-growing method)
python3 pe_partpy/gen_par_from_tri_regions.py tests/cylinder.tri --angle 45.0

# Visualize
python3 pe_partpy/tri2vtk_converter.py tests/cylinder_regions/file.prj \
    -proj tests/cylinder_regions
paraview tests/cylinder_regions/main.vtu
```

## File Formats

### MSH 4.2 (Input)
Gmsh native format with entity-based sections:
- `$MeshFormat`: Version 4.2
- `$Nodes`: Node coordinates grouped by entity
- `$Elements`: Element connectivity grouped by entity

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
- Line 2: Parameters (usually `''`)
- Lines 3+: 1-based node indices

### PRJ (Project)
Simple list format:
- Line 1: Mesh filename (e.g., `mesh.tri`)
- Lines 2+: Boundary filenames (e.g., `region_0.par`)

## Testing

Example test case: `tests/test_cylinder/`
- `simple_box`: 2×1×1 box, 64 hexahedra, 6 boundaries
- `cylinder`: O-grid cylinder, 384 hexahedra, 7 boundaries (2 caps + 4 inner + 1 outer)

## Contributing

This is a workflow integration project. To contribute:
1. Add new mesh generators to `workflow/generators/`
2. Enhance converters in `workflow/converters/`
3. Test with example cases in `tests/`

## License

See individual component repositories for license information.
