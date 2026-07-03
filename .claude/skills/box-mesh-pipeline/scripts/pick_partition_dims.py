#!/usr/bin/env python3
"""
Suggest a per-axis partition split (px, py, pz) for PyPartitioner.py's
axis_uniform strategy, given the mesh's cell counts per axis.

axis_uniform slices the mesh along coordinate planes, so each axis's
partition count must evenly divide that axis's cell count -- otherwise some
partitions get one extra/fewer layer of elements than others.

Beyond that hard constraint, the goal is to keep each partition's cell shape
(nx/px x ny/py x nz/pz) as close to a cube as possible -- highly elongated
partitions cause trouble in the simulation later. This is *not* the same as
requiring px == py == pz: for a roughly cube-shaped mesh that usually does
minimize elongation, but for an elongated mesh (e.g. 20x1x1, where y and z
only have one cell and can't be split further), splitting unevenly --
heavily along the long axis, not at all along the short ones -- is exactly
what keeps partitions close to the mesh's own shape. Forcing equal splits
there would either be impossible (no common divisor) or force a degenerate
1x1x1 "partition" of the whole mesh.

Usage:
    python3 pick_partition_dims.py --nx 8 --ny 8 --nz 8 [--target 2]
    python3 pick_partition_dims.py --nx 6 --ny 4 --nz 4 --total 4
    python3 pick_partition_dims.py --nx 20 --ny 1 --nz 1 --total 20
"""

import argparse


def divisors(n):
    return [d for d in range(1, n + 1) if n % d == 0]


def best_divisor_near(n, target):
    """Largest divisor of n that does not exceed target, falling back to 1."""
    candidates = [d for d in divisors(n) if d <= target]
    return max(candidates) if candidates else 1


def elongation(nx, ny, nz, px, py, pz):
    """How far a partition's cell shape is from cubic -- lower is better."""
    ex, ey, ez = nx / px, ny / py, nz / pz
    return max(ex, ey, ez) / min(ex, ey, ez)


def best_split_for_total(nx, ny, nz, total):
    """Least-elongated (px, py, pz) whose product equals total and that evenly
    divides (nx, ny, nz), or None if no such split exists."""
    best = None
    best_score = None
    for px in divisors(nx):
        if total % px != 0:
            continue
        for py in divisors(ny):
            if (total // px) % py != 0:
                continue
            pz = total // px // py
            if nz % pz != 0:
                continue
            score = elongation(nx, ny, nz, px, py, pz)
            if best_score is None or score < best_score:
                best_score = score
                best = (px, py, pz)
    return best


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nx", type=int, required=True, help="Mesh cells in x")
    ap.add_argument("--ny", type=int, required=True, help="Mesh cells in y")
    ap.add_argument("--nz", type=int, required=True, help="Mesh cells in z")
    ap.add_argument(
        "--target", type=int, default=2,
        help="Preferred partitions per axis before falling back to a smaller divisor "
             "(default: 2). Ignored if --total is given.",
    )
    ap.add_argument(
        "--total", type=int, default=None,
        help="Exact total partition count to hit, e.g. requested by the user. Searches "
             "for the split whose product equals this, divides nx/ny/nz evenly, and "
             "leaves partitions as close to cubic as possible.",
    )
    args = ap.parse_args()

    if args.total is not None:
        split = best_split_for_total(args.nx, args.ny, args.nz, args.total)
        if split is None:
            print(f"# No split of nx={args.nx}, ny={args.ny}, nz={args.nz} multiplies to "
                  f"{args.total} while evenly dividing each axis. Pick a different total "
                  f"or mesh resolution.")
            return
        px, py, pz = split
    else:
        px = best_divisor_near(args.nx, args.target)
        py = best_divisor_near(args.ny, args.target)
        pz = best_divisor_near(args.nz, args.target)

    spec = f"x{px}-y{py}-z{pz}"
    total = px * py * pz

    print(spec)
    print(f"# total partitions: {total}  (elements per partition: "
          f"{args.nx // px} x {args.ny // py} x {args.nz // pz} cells)")


if __name__ == "__main__":
    main()
