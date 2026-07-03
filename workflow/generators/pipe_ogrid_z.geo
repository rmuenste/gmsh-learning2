// Periodic pipe mesh: butterfly O-grid cross-section, pure z-extrusion
//
// z-axis pipe centered on (0,0), R = 0.5, z in [0, L]. True 5-block
// butterfly (square core + 4 outer blocks), so there is no pinched
// center like the 4-quadrant cylinder_structured.geo.
//
// Coarse resolution: 48 cells/cross-section (8 across the diameter),
// nLayers quasi-uniform axial layers. With 2 refinements this gives
// 768 cells/section x 4*nLayers layers (h ~ 0.03 at nLayers = 27).
// Keep nLayers divisible by 27 for the 1x1x27 slab decomposition.
//
// End faces at z=0 and z=L are exact translated copies (pure extrusion);
// boundary tagging (Wall hull + Periodic caps) happens downstream via
// workflow/tag_pipe_boundaries.py.
//
// Usage:
//   python3 workflow/run_geo_to_case.py workflow/generators/pipe_ogrid_z.geo \
//       --outdir cases/pipe_ogrid_z --tag-pipe-boundaries
//   L=4 variant: --setnumber L=4.0 --setnumber nLayers=54

SetFactory("Built-in");

DefineConstant[
  L       = {2.0, Name "Parameters/L"},       // pipe length (axial period)
  nLayers = {27,  Name "Parameters/nLayers"}  // axial layers, keep divisible by 27
];

R        = 0.5;   // fixed: hull .par descriptor hardcodes 0.5d0
coreFrac = 0.6;   // core corner radius / R (balances core vs radial cell sizes)
nSec     = 4;     // cells per core edge and per 90-degree arc
nRad     = 2;     // radial cells between core and wall

rc = coreFrac * R;
c  = rc / Sqrt(2);  // core corner coordinate
w  = R  / Sqrt(2);  // wall point coordinate on the diagonal

// Arc center (never meshed)
Point(1) = {0, 0, 0, 1.0};

// Core corners on the diagonals (45 + 90k degrees)
Point(2) = { c,  c, 0, 1.0};
Point(3) = {-c,  c, 0, 1.0};
Point(4) = {-c, -c, 0, 1.0};
Point(5) = { c, -c, 0, 1.0};

// Wall points on the same diagonals
Point(6) = { w,  w, 0, 1.0};
Point(7) = {-w,  w, 0, 1.0};
Point(8) = {-w, -w, 0, 1.0};
Point(9) = { w, -w, 0, 1.0};

// Core edges
Line(1) = {2, 3};  // top
Line(2) = {3, 4};  // left
Line(3) = {4, 5};  // bottom
Line(4) = {5, 2};  // right

// Radial spokes
Line(5) = {2, 6};
Line(6) = {3, 7};
Line(7) = {4, 8};
Line(8) = {5, 9};

// Wall arcs (90 degrees each)
Circle(9)  = {6, 1, 7};  // top
Circle(10) = {7, 1, 8};  // left
Circle(11) = {8, 1, 9};  // bottom
Circle(12) = {9, 1, 6};  // right

// Core block
Curve Loop(1) = {1, 2, 3, 4};
Plane Surface(1) = {1};

// Outer blocks
Curve Loop(2) = {1, 6, -9, -5};    // top
Plane Surface(2) = {2};
Curve Loop(3) = {2, 7, -10, -6};   // left
Plane Surface(3) = {3};
Curve Loop(4) = {3, 8, -11, -7};   // bottom
Plane Surface(4) = {4};
Curve Loop(5) = {4, 5, -12, -8};   // right
Plane Surface(5) = {5};

// Structured quads: 4x4 core + 4 blocks of 4 circumferential x 2 radial
Transfinite Curve {1, 2, 3, 4, 9, 10, 11, 12} = nSec + 1;
Transfinite Curve {5, 6, 7, 8} = nRad + 1;
Transfinite Surface {1, 2, 3, 4, 5};
Recombine Surface {1, 2, 3, 4, 5};

// Pure translational extrusion -> congruent end faces at z=0 and z=L
out[] = Extrude {0, 0, L} {
  Surface{1, 2, 3, 4, 5}; Layers{nLayers}; Recombine;
};

// With Mesh.SaveAll = 0, restricting output to the extruded volumes keeps
// arc-center construction nodes (orphans) out of the VTK/TRI.
Physical Volume("fluid") = {out[1], out[7], out[13], out[19], out[25]};

Mesh 3;

Printf("pipe_ogrid_z: expected hexas = %g, expected nodes = %g",
       (nSec*nSec + 4*nSec*nRad) * nLayers,
       ((nSec+1)*(nSec+1) + 4*nSec*nRad) * (nLayers+1));

Mesh.SaveAll = 0;
Save "pipe_ogrid_z.vtk";
