// Simple hexahedral cylinder mesh for testing
// Generates a structured hex mesh using transfinite volumes

SetFactory("OpenCASCADE");

// Parameters
radius = 1.0;
height = 2.0;
n_radial = 4;    // divisions in radial direction
n_circum = 12;   // divisions around circumference
n_height = 8;    // divisions in height

// Create cylinder
Cylinder(1) = {0, 0, 0, 0, 0, height, radius};

// Get surfaces
surfaces[] = Surface{:};

// Apply transfinite meshing
Transfinite Surface {:};
Recombine Surface {:};

// Make the volume transfinite
Transfinite Volume {:};

// Set mesh size
Mesh.CharacteristicLengthMin = 0.1;
Mesh.CharacteristicLengthMax = 0.5;

// Force hexahedral meshing
Mesh.RecombineAll = 1;
Mesh.RecombinationAlgorithm = 2; // Simple full-quad
Mesh.SubdivisionAlgorithm = 1;   // All hexas

// Generate 3D mesh
Mesh 3;

// Save in MSH 4.2 format (ASCII)
Mesh.MshFileVersion = 4.2;
Save "cylinder_hex.msh";
