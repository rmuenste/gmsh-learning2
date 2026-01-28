#!/bin/bash
# Setup script for gmsh-learning2 workflow
# This script manages the two dependent repositories

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Gmsh-Learning2 Workflow Setup ==="
echo

# Ensure repos exist (clone if missing)
if [ ! -d "gmsh-learning" ]; then
    echo "gmsh-learning not found; cloning via SSH (fallback to HTTPS if SSH keys aren't set up)..."
    git clone git@github.com:rmuenste/gmsh-learning.git gmsh-learning || \
      git clone https://github.com/rmuenste/gmsh-learning2.git gmsh-learning
    echo "✓ Cloned gmsh-learning"
else
    echo "✓ Found gmsh-learning"
fi

if [ ! -d "pe_partpy" ]; then
    echo "pe_partpy not found; cloning via SSH (fallback to HTTPS if SSH keys aren't set up)..."
    git clone git@github.com:rmuenste/pe_partpy.git pe_partpy || \
      git clone https://github.com/rmuenste/pe_partpy.git pe_partpy
    echo "✓ Cloned pe_partpy"
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
