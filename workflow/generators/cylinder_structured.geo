// Structured hexahedral cylinder mesh using extrusion
// Creates cylinder from a structured O-grid cross-section

SetFactory("Built-in");

// Parameters
radius = 1.0;
height = 2.0;
n_radial = 3;      // radial divisions
n_circum = 16;     // circumferential divisions
n_height = 8;      // height divisions

// Create center point
Point(1) = {0, 0, 0, 1.0};

// Create inner square (will become center region)
inner_size = radius * 0.3;
Point(2) = {inner_size, 0, 0, 1.0};
Point(3) = {0, inner_size, 0, 1.0};
Point(4) = {-inner_size, 0, 0, 1.0};
Point(5) = {0, -inner_size, 0, 1.0};

// Create outer circle points
Point(6) = {radius, 0, 0, 1.0};
Point(7) = {0, radius, 0, 1.0};
Point(8) = {-radius, 0, 0, 1.0};
Point(9) = {0, -radius, 0, 1.0};

// Inner square lines
Line(1) = {2, 3};
Line(2) = {3, 4};
Line(3) = {4, 5};
Line(4) = {5, 2};

// Outer arcs
Circle(5) = {6, 1, 7};
Circle(6) = {7, 1, 8};
Circle(7) = {8, 1, 9};
Circle(8) = {9, 1, 6};

// Radial lines
Line(9) = {2, 6};
Line(10) = {3, 7};
Line(11) = {4, 8};
Line(12) = {5, 9};

// Create 4 surfaces (O-grid quadrants)
Curve Loop(1) = {1, 10, -5, -9};
Plane Surface(1) = {1};

Curve Loop(2) = {2, 11, -6, -10};
Plane Surface(2) = {2};

Curve Loop(3) = {3, 12, -7, -11};
Plane Surface(3) = {3};

Curve Loop(4) = {4, 9, -8, -12};
Plane Surface(4) = {4};

// Make surfaces transfinite
Transfinite Curve {1, 2, 3, 4} = n_circum/4 + 1;
Transfinite Curve {5, 6, 7, 8} = n_circum/4 + 1;
Transfinite Curve {9, 10, 11, 12} = n_radial + 1;

Transfinite Surface {1, 2, 3, 4};
Recombine Surface {1, 2, 3, 4};

// Extrude to create cylinder
out[] = Extrude {0, 0, height} {
  Surface{1, 2, 3, 4}; Layers{n_height}; Recombine;
};

// Generate mesh
Mesh 3;

// Save as MSH 4.2
Mesh.MshFileVersion = 4.2;
