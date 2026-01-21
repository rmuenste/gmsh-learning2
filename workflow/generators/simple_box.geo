// Minimal working structured hexahedral mesh
SetFactory("Built-in");

// Box dimensions
lx = 2.0;
ly = 1.0;
lz = 1.0;

// Mesh divisions
nx = 8;
ny = 4;
nz = 4;

// Create box using OpenCASCADE (simpler for basic shapes)
SetFactory("OpenCASCADE");
Box(1) = {0, 0, 0, lx, ly, lz};

// Get all curves and surfaces
surfaces() = Surface{:};
curves() = Curve{:};

// Set transfinite on all curves
For i In {0:#curves()-1}
  Transfinite Curve{curves(i)} = 5;
EndFor

// Set transfinite on all surfaces
Transfinite Surface{:};
Recombine Surface{:};

// Set transfinite on volume
Transfinite Volume{:};

// Generate mesh
Mesh 3;

// Save as MSH 4.2
Mesh.MshFileVersion = 4.2;
