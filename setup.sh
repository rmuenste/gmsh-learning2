#!/bin/bash
# Setup script for gmsh-learning2 workflow
# This script manages the two dependent repositories

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Gmsh-Learning2 Workflow Setup ==="
echo

# Check if repos exist
if [ ! -d "gmsh-learning" ]; then
    echo "Error: gmsh-learning directory not found"
    echo "Please clone or link the gmsh-learning repository"
    exit 1
else
    echo "✓ Found gmsh-learning"
fi

if [ ! -d "pe_partpy" ]; then
    echo "Error: pe_partpy directory not found"
    echo "Please clone or link the pe_partpy repository"
    exit 1
else
    echo "✓ Found pe_partpy"
fi

# Check for Gmsh installation
if command -v gmsh &> /dev/null; then
    GMSH_VERSION=$(gmsh --version 2>&1 | head -1 || echo "unknown")
    echo "✓ Found Gmsh: $GMSH_VERSION"
else
    echo "⚠ Warning: gmsh not found in PATH"
    echo "  Please install Gmsh 4.x from http://gmsh.info"
fi

# Check for Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✓ Found $PYTHON_VERSION"
else
    echo "✗ Error: python3 not found"
    exit 1
fi

# Check for numpy
if python3 -c "import numpy" 2>/dev/null; then
    echo "✓ Found numpy"
else
    echo "⚠ Warning: numpy not installed"
    echo "  Install with: pip3 install numpy"
fi

echo
echo "=== Setup Complete ==="
echo
echo "Workflow structure:"
echo "  workflow/generators/  - Gmsh mesh generation scripts"
echo "  workflow/converters/  - Format conversion tools"
echo "  tests/test_cylinder/  - Test output directory"
echo
echo "Example usage:"
echo "  1. Generate mesh:"
echo "     cd workflow/generators"
echo "     gmsh simple_box.geo -3 -o ../../tests/test_cylinder/my_mesh.msh"
echo
echo "  2. Convert to VTK/TRI:"
echo "     python3 workflow/converters/msh_to_vtk.py tests/test_cylinder/my_mesh.msh"
echo
echo "  3. View in ParaView:"
echo "     paraview tests/test_cylinder/my_mesh.vtk"
echo
