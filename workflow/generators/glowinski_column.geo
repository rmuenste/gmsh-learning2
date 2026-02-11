// Glowinski fluidized bed benchmark - structured hex mesh
// Slit bed column with boundary layer cells near walls
// Coordinate mapping: width -> x, depth -> y, height -> z (CGS units)
SetFactory("Built-in");

// Domain dimensions [cm]
Lx = 20.30;
Ly = 0.686;
Lz = 70.22;

// Mesh parameters
nx_int = 59;   // interior x-cells
ny_int = 2;    // interior y-cells
nz     = 205;  // z-layers (uniform)
n_bl   = 1;    // boundary layer cells per side
delta  = 0.1;  // BL thickness per side [cm]

// Derived
dx = delta;  // = 0.2
dy = delta;  // = 0.2

// Characteristic length (not used for structured mesh, but required by Point)
lc = 1.0;

// ============================================================
// 16 Points forming 2 nested rectangles in z=0 plane
// ============================================================
//
// P4(0,Ly) ------P14(dx,Ly)----------------P13(Lx-dx,Ly)------P3(Lx,Ly)
//   |               |                           |                  |
// P15(0,Ly-dy)   P8(dx,Ly-dy)-------------P7(Lx-dx,Ly-dy)   P12(Lx,Ly-dy)
//   |               |                           |                  |
//   |               |        INTERIOR            |                  |
//   |               |        59 x 2              |                  |
//   |               |                           |                  |
// P16(0,dy)------P5(dx,dy)-----------------P6(Lx-dx,dy)-------P11(Lx,dy)
//   |               |                           |                  |
// P1(0,0) -------P9(dx,0)-----------------P10(Lx-dx,0)-------P2(Lx,0)

// Outer corners
Point(1)  = {0,      0,      0, lc};
Point(2)  = {Lx,     0,      0, lc};
Point(3)  = {Lx,     Ly,     0, lc};
Point(4)  = {0,      Ly,     0, lc};

// Inner rectangle
Point(5)  = {dx,     dy,     0, lc};
Point(6)  = {Lx-dx,  dy,     0, lc};
Point(7)  = {Lx-dx,  Ly-dy,  0, lc};
Point(8)  = {dx,     Ly-dy,  0, lc};

// Bottom edge intermediates
Point(9)  = {dx,     0,      0, lc};
Point(10) = {Lx-dx,  0,      0, lc};

// Right edge intermediates
Point(11) = {Lx,     dy,     0, lc};
Point(12) = {Lx,     Ly-dy,  0, lc};

// Top edge intermediates
Point(13) = {Lx-dx,  Ly,     0, lc};
Point(14) = {dx,     Ly,     0, lc};

// Left edge intermediates
Point(15) = {0,      Ly-dy,  0, lc};
Point(16) = {0,      dy,     0, lc};

// ============================================================
// 24 Lines
// ============================================================

// Bottom row (horizontal, left to right)
Line(1)  = {1, 9};     // BL left
Line(2)  = {9, 10};    // interior
Line(3)  = {10, 2};    // BL right

// Second row (horizontal)
Line(4)  = {16, 5};    // BL left
Line(5)  = {5, 6};     // interior
Line(6)  = {6, 11};    // BL right

// Third row (horizontal)
Line(7)  = {15, 8};    // BL left
Line(8)  = {8, 7};     // interior
Line(9)  = {7, 12};    // BL right

// Top row (horizontal)
Line(10) = {4, 14};    // BL left
Line(11) = {14, 13};   // interior
Line(12) = {13, 3};    // BL right

// Left column (vertical, bottom to top)
Line(13) = {1, 16};    // BL bottom
Line(14) = {16, 15};   // interior
Line(15) = {15, 4};    // BL top

// Second column (vertical)
Line(16) = {9, 5};     // BL bottom
Line(17) = {5, 8};     // interior
Line(18) = {8, 14};    // BL top

// Third column (vertical)
Line(19) = {10, 6};    // BL bottom
Line(20) = {6, 7};     // interior
Line(21) = {7, 13};    // BL top

// Right column (vertical)
Line(22) = {2, 11};    // BL bottom
Line(23) = {11, 12};   // interior
Line(24) = {12, 3};    // BL top

// ============================================================
// 9 Surfaces (all CCW oriented)
// ============================================================

// Row 1 (bottom): y = 0..dy
Curve Loop(1) = {1, 16, -4, -13};       // S1: bottom-left corner
Plane Surface(1) = {1};

Curve Loop(2) = {2, 19, -5, -16};       // S2: bottom-center
Plane Surface(2) = {2};

Curve Loop(3) = {3, 22, -6, -19};       // S3: bottom-right corner
Plane Surface(3) = {3};

// Row 2 (middle): y = dy..(Ly-dy)
Curve Loop(4) = {4, 17, -7, -14};       // S4: middle-left
Plane Surface(4) = {4};

Curve Loop(5) = {5, 20, -8, -17};       // S5: center (interior)
Plane Surface(5) = {5};

Curve Loop(6) = {6, 23, -9, -20};       // S6: middle-right
Plane Surface(6) = {6};

// Row 3 (top): y = (Ly-dy)..Ly
Curve Loop(7) = {7, 18, -10, -15};      // S7: top-left corner
Plane Surface(7) = {7};

Curve Loop(8) = {8, 21, -11, -18};      // S8: top-center
Plane Surface(8) = {8};

Curve Loop(9) = {9, 24, -12, -21};      // S9: top-right corner
Plane Surface(9) = {9};

// ============================================================
// Transfinite curves
// ============================================================

// BL x-segments (left): n_bl+1 nodes
Transfinite Curve {1, 4, 7, 10} = n_bl + 1;
// BL x-segments (right)
Transfinite Curve {3, 6, 9, 12} = n_bl + 1;
// Interior x-segments
Transfinite Curve {2, 5, 8, 11} = nx_int + 1;

// BL y-segments (bottom): n_bl+1 nodes
Transfinite Curve {13, 16, 19, 22} = n_bl + 1;
// BL y-segments (top)
Transfinite Curve {15, 18, 21, 24} = n_bl + 1;
// Interior y-segments
Transfinite Curve {14, 17, 20, 23} = ny_int + 1;

// ============================================================
// Transfinite surfaces + recombine for quads
// ============================================================
Transfinite Surface {1, 2, 3, 4, 5, 6, 7, 8, 9};
Recombine Surface {1, 2, 3, 4, 5, 6, 7, 8, 9};

// ============================================================
// Extrude in z (uniform layers)
// ============================================================
e1[] = Extrude {0, 0, Lz} { Surface{1}; Layers{nz}; Recombine; };
e2[] = Extrude {0, 0, Lz} { Surface{2}; Layers{nz}; Recombine; };
e3[] = Extrude {0, 0, Lz} { Surface{3}; Layers{nz}; Recombine; };
e4[] = Extrude {0, 0, Lz} { Surface{4}; Layers{nz}; Recombine; };
e5[] = Extrude {0, 0, Lz} { Surface{5}; Layers{nz}; Recombine; };
e6[] = Extrude {0, 0, Lz} { Surface{6}; Layers{nz}; Recombine; };
e7[] = Extrude {0, 0, Lz} { Surface{7}; Layers{nz}; Recombine; };
e8[] = Extrude {0, 0, Lz} { Surface{8}; Layers{nz}; Recombine; };
e9[] = Extrude {0, 0, Lz} { Surface{9}; Layers{nz}; Recombine; };

// Extrude output per surface:
//   e[0] = top face,  e[1] = volume
//   e[2..5] = lateral faces (in curve loop order)

// ============================================================
// Physical groups
// ============================================================

// Inlet: 9 bottom faces at z=0
Physical Surface("inlet") = {1, 2, 3, 4, 5, 6, 7, 8, 9};

// Outlet: 9 top faces at z=Lz
Physical Surface("outlet") = {e1[0], e2[0], e3[0], e4[0], e5[0],
                               e6[0], e7[0], e8[0], e9[0]};

// Wall at y=0: lateral faces from bottom-row surfaces (1st curve in their loops)
// S1 loop {1,...}: e1[2] from L1 (P1->P9, y=0)
// S2 loop {2,...}: e2[2] from L2 (P9->P10, y=0)
// S3 loop {3,...}: e3[2] from L3 (P10->P2, y=0)
Physical Surface("wall_ymin") = {e1[2], e2[2], e3[2]};

// Wall at x=Lx: lateral faces from right-column surfaces (2nd curve in their loops)
// S3 loop {...,22,...}: e3[3] from L22 (P2->P11, x=Lx)
// S6 loop {...,23,...}: e6[3] from L23 (P11->P12, x=Lx)
// S9 loop {...,24,...}: e9[3] from L24 (P12->P3, x=Lx)
Physical Surface("wall_xmax") = {e3[3], e6[3], e9[3]};

// Wall at y=Ly: lateral faces from top-row surfaces (3rd curve in their loops)
// S7 loop {...,-10,...}: e7[4] from -L10 (P14->P4, y=Ly)
// S8 loop {...,-11,...}: e8[4] from -L11 (P13->P14, y=Ly)
// S9 loop {...,-12,...}: e9[4] from -L12 (P3->P13, y=Ly)
Physical Surface("wall_ymax") = {e7[4], e8[4], e9[4]};

// Wall at x=0: lateral faces from left-column surfaces (4th curve in their loops)
// S1 loop {...,-13}: e1[5] from -L13 (P16->P1, x=0)
// S4 loop {...,-14}: e4[5] from -L14 (P15->P16, x=0)
// S7 loop {...,-15}: e7[5] from -L15 (P4->P15, x=0)
Physical Surface("wall_xmin") = {e1[5], e4[5], e7[5]};

// Fluid volume: all 9 extruded volumes
Physical Volume("fluid") = {e1[1], e2[1], e3[1], e4[1], e5[1],
                             e6[1], e7[1], e8[1], e9[1]};

// ============================================================
// Output settings
// ============================================================
Mesh.MshFileVersion = 4.2;
