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
