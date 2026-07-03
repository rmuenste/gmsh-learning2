---
name: box-mesh-pipeline
description: Generate a structured hexahedral box or unit-cube mesh and carry it all the way through to a partitioned, CFD-ready case using pe_partpy. Use this whenever the user asks to create, generate, or build a box mesh, cube mesh, unit cube, rectangular domain mesh, or structured hex mesh in this repo, or wants that mesh partitioned/split into subdomains for parallel CFD -- even if they only describe dimensions and resolution without naming a script. Also use it if they ask to visualize or partition a mesh that came from this pipeline.
---

# Box / Cube Mesh Pipeline

This repo can build a structured hexahedral box mesh and push it straight through to
partitioned subdomains without touching Gmsh at all. The whole thing runs through
`pe_partpy`, using `unit_cube_vtk.py` to build the grid directly with the VTK Python API.

This is a five-stage pipeline. Run all five stages unless the user explicitly asks to stop
earlier (e.g. "just give me the vtk" or "I don't need it partitioned").

## Stage 0: confirm parameters

Before running anything, work out:

- **Bounds**: `x0,x1,y0,y1,z0,z1`. Default to the unit cube `[0,1]^3` if the user just says
  "a cube" or "unit cube" without dimensions.
- **Cell counts**: `nx, ny, nz`. If unspecified, a small value like 4-8 per axis is enough for
  a test/visualization mesh; ask if the user needs something finer for an actual solve.
- **Output location**: pick a working directory, e.g. `tests/<name>/`, and keep all
  intermediate files there so the case is self-contained.

## Stage 1: generate the box mesh (.vtk)

```bash
python3 pe_partpy/unit_cube_vtk.py --out <case_dir>/box.vtk \
  --nx <nx> --ny <ny> --nz <nz> \
  --x0 <x0> --x1 <x1> --y0 <y0> --y1 <y1> --z0 <z0> --z1 <z1>
```

The `--x0/--x1/--y0/--y1/--z0/--z1` flags default to `0.0/1.0` each, so they can be omitted
entirely for a unit cube. This script needs the `vtk` Python package. If `import vtk` fails,
install it into whatever environment is active (e.g. `pip install vtk` or into the repo's
`.venv` if one exists at the repo root) rather than falling back to Gmsh -- the Gmsh `.geo`
route (`workflow/generators/box_hex.geo`) is a heavier alternative that's only worth reaching
for if VTK truly cannot be installed.

## Stage 2: convert to .tri

`unit_cube_vtk.py` only writes `.vtk` -- it does not produce a `.tri` file directly. Convert
with `tri2vtk_converter.py`, which despite its name handles both directions based on the file
extensions of its two positional arguments:

```bash
python3 pe_partpy/tri2vtk_converter.py <case_dir>/box.vtk <case_dir>/box.tri
```

## Stage 3: boundary parametrization

Box/cube faces are perfectly axis-aligned, so use the axis-aligned detector (not the
region-growing one, which is for curved geometry):

```bash
python3 pe_partpy/gen_par_from_tri.py <case_dir>/box.tri --outdir <case_dir>/regions
```

This writes `<case_dir>/regions/file.prj` plus one `.par` file per face
(`xmin/xmax/ymin/ymax/zmin/zmax`).

## Stage 4: partition with axis_uniform

For a structured box mesh, use the `axis_uniform` strategy. It slices along coordinate
planes and needs no external library (METIS is for unstructured/general meshes and isn't
needed here, and may not even load on every platform -- e.g. a bundled `libmetis.so` built
for a different CPU architecture than the host will fail to load).

`axis_uniform` requires the **partition count on each axis to evenly divide that axis's
cell count** -- otherwise some partitions end up with an extra or missing layer of elements.
Beyond that hard constraint, the goal is to keep each partition's cell shape as close to
cubic as possible -- highly elongated partitions cause trouble in the simulation later.
That is *not* the same as always using the same split count on every axis: for a roughly
cube-shaped mesh, an equal split (e.g. `x2-y2-z2`) usually is the least-elongated option, but
for an elongated mesh (e.g. 20x1x1, where y and z have only one cell and can't be split
further), the least-elongated split is necessarily uneven -- heavily along the long axis,
not at all along the short ones (e.g. `x10-y1-z1`). Use the bundled helper, which searches
for the least-elongated valid split, instead of guessing:

```bash
python3 scripts/pick_partition_dims.py --nx <nx> --ny <ny> --nz <nz>
```

It prints a spec like `x2-y2-z2` along with the resulting partition count and elements per
partition. By default it picks, independently per axis, the largest divisor of that axis's
cell count up to 2 (falling back to 1 where the axis has no divisor in range, e.g. an axis
with an odd cell count, or only 1 cell to begin with). Pass `--target <n>` to bias toward a
larger per-axis split when the mesh resolution supports it.

If the user asked for a specific total partition count (e.g. "partition into 4 parts"), pass
`--total <n>` instead -- it searches every per-axis combination whose product equals that
total and that evenly divides nx/ny/nz, and picks whichever leaves partitions least
elongated:

```bash
python3 scripts/pick_partition_dims.py --nx <nx> --ny <ny> --nz <nz> --total <n>
```

If no valid split exists for that exact total, it says so rather than guessing -- in that
case, tell the user their requested count doesn't factor cleanly into the mesh resolution
and suggest the nearest one that does.

Then partition:

```bash
python3 pe_partpy/PyPartitioner.py <NPart> axis_uniform <spec> <MeshName> <case_dir>/regions/file.prj
```

- `<NPart>` is the total partition count (the product of the per-axis split, e.g. 8 for
  `x2-y2-z2`).
- `<MeshName>` is a short uppercase-ish tag used to name the output folder; reuse the case
  name.
- This must be run with the **named** strategy string (`axis_uniform`), not a legacy numeric
  code -- `PyPartitioner.py --help` lists the current strategy names if anything here seems
  out of date.

Output lands in `_mesh/<MeshName>/` (subdirectories per partition, or a flat layout for a
single partition).

## Stage 5 (optional): visualize

To inspect the unpartitioned case in ParaView:

```bash
python3 pe_partpy/tri2vtk_converter.py <case_dir>/regions/file.prj -proj <case_dir>/regions
```

This writes `<case_dir>/regions/main.vtu`. For the partitioned output, point ParaView at the
per-partition files under `_mesh/<MeshName>/`.

## Notes

- All five stages were verified end-to-end while building this skill: `unit_cube_vtk.py` to
  `.vtk`, `tri2vtk_converter.py` to `.tri`, `gen_par_from_tri.py` for boundaries, and
  `PyPartitioner.py` with `axis_uniform` for partitioning all work without needing METIS or
  Gmsh.
- `pe_partpy/CLAUDE.md` documents `PyPartitioner.py`'s argument order using legacy numeric
  strategy codes (e.g. method `1`). The installed script now requires the named strategy
  instead (`metis_recursive` rather than `1`, `axis_uniform` rather than `-4`, etc.) --
  trust `--help` output over that doc if they disagree.
