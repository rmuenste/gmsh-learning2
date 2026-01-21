// Simple structured hexahedral box mesh for testing
// Uses built-in geometry kernel with transfinite meshing

// Parameters
lx = 2.0;  // length in x
ly = 2.0;  // length in y
lz = 3.0;  // length in z
nx = 4;    // divisions in x
ny = 4;    // divisions in y
nz = 6;    // divisions in z

// Define 8 corner points
Point(1) = {0, 0, 0, 1.0};
Point(2) = {lx, 0, 0, 1.0};
Point(3) = {lx, ly, 0, 1.0};
Point(4) = {0, ly, 0, 1.0};
Point(5) = {0, 0, lz, 1.0};
Point(6) = {lx, 0, lz, 1.0};
Point(7) = {lx, ly, lz, 1.0};
Point(8) = {0, ly, lz, 1.0};

// Bottom face edges
Line(1) = {1, 2};
Line(2) = {2, 3};
Line(3) = {3, 4};
Line(4) = {4, 1};

// Top face edges
Line(5) = {5, 6};
Line(6) = {6, 7};
Line(7) = {7, 8};
Line(8) = {8, 5};

// Vertical edges
Line(9) = {1, 5};
Line(10) = {2, 6};
Line(11) = {3, 7};
Line(12) = {4, 8};

// Define 6 surfaces (bottom, top, and 4 sides)
// All surfaces must have compatible orientations for Transfinite Volume

// Bottom (z=0)
Curve Loop(1) = {1, 2, 3, 4};
Plane Surface(1) = {1};

// Top (z=lz)
Curve Loop(2) = {-5, -6, -7, -8};
Plane Surface(2) = {2};

// Side 1 (x=0)
Curve Loop(3) = {-4, -12, 8, 9};
Plane Surface(3) = {3};

// Side 2 (y=0)
Curve Loop(4) = {1, 10, -5, -9};
Plane Surface(4) = {4};

// Side 3 (x=lx)
Curve Loop(5) = {-2, -10, 6, 11};
Plane Surface(5) = {5};

// Side 4 (y=ly)
Curve Loop(6) = {-3, -11, 7, 12};
Plane Surface(6) = {6};

// Define volume
Surface Loop(1) = {1, 2, 3, 4, 5, 6};
Volume(1) = {1};

// Apply transfinite meshing to all curves
Transfinite Curve {1, 2, 3, 4, 5, 6, 7, 8} = nx + 1;
Transfinite Curve {9, 10, 11, 12} = nz + 1;

// Apply transfinite meshing to all surfaces
Transfinite Surface {:};
Recombine Surface {:};

// Apply transfinite meshing to volume
Transfinite Volume {:};

// Ensure hexahedral meshing
Mesh.RecombineAll = 1;

// Generate 3D mesh
Mesh 3;

// Save in MSH 4.2 format (ASCII)
Mesh.MshFileVersion = 4.2;
