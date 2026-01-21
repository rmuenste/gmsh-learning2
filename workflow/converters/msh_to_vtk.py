#!/usr/bin/env python3
"""
Converter from Gmsh MSH 4.x format to VTK and TRI formats

Usage:
    python msh_to_vtk.py input.msh [output_basename]

Outputs:
    - output_basename.vtk (VTK ASCII format for ParaView)
    - output_basename.tri (TRI format for CFD solver)
"""

import sys
import os

# Add pe_partpy to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(os.path.dirname(script_dir))
pe_partpy_path = os.path.join(repo_root, 'pe_partpy')
sys.path.insert(0, pe_partpy_path)

from mesh.mesh_io import readHexMeshFileMSH4, writeHexMeshVTK, writeTriFile


def convert_msh_to_formats(msh_file, output_basename=None):
    """
    Convert MSH 4.x file to VTK and TRI formats

    Args:
        msh_file: Path to input .msh file
        output_basename: Base name for output files (without extension)
                        If None, uses input filename
    """

    # Generate output basename if not provided
    if output_basename is None:
        output_basename = os.path.splitext(msh_file)[0]

    print(f"Reading mesh from: {msh_file}")

    # Read the hex mesh
    try:
        hex_mesh = readHexMeshFileMSH4(msh_file)
    except Exception as e:
        print(f"Error reading MSH file: {e}")
        return False

    print(f"  Nodes: {len(hex_mesh.nodes)}")
    print(f"  Hexahedra: {len(hex_mesh.hexas)}")

    # Write VTK file
    vtk_file = output_basename + ".vtk"
    print(f"\nWriting VTK to: {vtk_file}")
    try:
        writeHexMeshVTK(hex_mesh, vtk_file)
        print(f"  Successfully wrote VTK file")
    except Exception as e:
        print(f"  Error writing VTK file: {e}")
        return False

    # Write TRI file
    tri_file = output_basename + ".tri"
    print(f"\nWriting TRI to: {tri_file}")
    try:
        writeTriFile(hex_mesh, tri_file)
        print(f"  Successfully wrote TRI file")
    except Exception as e:
        print(f"  Error writing TRI file: {e}")
        return False

    print(f"\nConversion complete!")
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python msh_to_vtk.py input.msh [output_basename]")
        print("\nExample:")
        print("  python msh_to_vtk.py mesh.msh")
        print("  python msh_to_vtk.py mesh.msh my_output")
        sys.exit(1)

    msh_file = sys.argv[1]

    if not os.path.exists(msh_file):
        print(f"Error: File not found: {msh_file}")
        sys.exit(1)

    output_basename = sys.argv[2] if len(sys.argv) > 2 else None

    success = convert_msh_to_formats(msh_file, output_basename)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
