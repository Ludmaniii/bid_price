"""
check_dp.py — check the dynamic programme in build.py against independent methods.

Part 1: random small cases.
   200 random matrices f (1-7 points, 1-5 candidate values). Every monotone sequence
   is listed, its jumps are counted, and the best one is compared with the DP,
   with no jump limit and with at most 0, 1, 2 jumps. Random matrices reach every
   branch of the DP; real days do not (their optimal curves use few, large jumps),
   so this part is the test of correctness.

Part 2: every day in caiso_sp15.csv. The DP is compared with two methods.

1. Enumeration, for at most S jumps (S = 0 .. S_MAX).
   A monotone sequence with exactly j jumps is fixed by two choices:
     - the j positions where q increases, and
     - the j+1 strictly increasing candidate values it takes.
   Listing every such pair lists every monotone sequence with j jumps exactly once,
   so the best of them is the exact optimum under the cap.

2. Integer programming, with no jump limit.
   Without a cap a day has 10^15 or more monotone sequences, too many to list.
   The same problem is written as a 0-1 programme and solved exactly with HiGHS
   (scipy.optimize.milp).

It also checks that every path the DP returns is monotone, respects the cap and
earns exactly the value the DP reports, and that
single price <= at most one jump <= unrestricted.

Run fetch.py first to create caiso_sp15.csv.
"""

import sys
import time
from itertools import combinations, combinations_with_replacement

import numpy as np
import pandas as pd
from scipy.optimize import LinearConstraint, milp
from scipy.sparse import coo_matrix

from build import build_points, single_price, solve

CSV = "caiso_sp15.csv"
ALPHA, BETA, CAP = 0.9, 0.05, 6.0
S_MAX = 3      # caps checked by enumeration on real days (S = 3 lists up to ~6e8 curves per day)
N_RANDOM = 200
TOL = 1e-6


def random_cases(n=N_RANDOM, seed=0):
    """Part 1: list every monotone sequence of small random matrices and compare with the DP."""
    rng = np.random.default_rng(seed)
    bad = 0
    for _ in range(n):
        K, M = int(rng.integers(1, 8)), int(rng.integers(1, 6))
        f = rng.normal(size=(K, M))
        seqs = list(combinations_with_replacement(range(M), K))   # all monotone sequences
        value = lambda s: sum(f[k, s[k]] for k in range(K))
        jumps = lambda s: sum(s[k] > s[k - 1] for k in range(1, K))
        for S in [None, 0, 1, 2]:
            brute = max(value(s) for s in seqs if S is None or jumps(s) <= S)
            v_dp, path = solve(f, S)
            if not (close(v_dp, brute) and path_ok(f, path, v_dp, S)):
                bad += 1
    print(f"random cases: {n} matrices x 4 caps, {bad} mismatches")
    return bad == 0


def enumerate_best(f, S):
    """Best total over all monotone sequences with at most S jumps, by listing every one."""
    K, M = f.shape
    P = np.vstack([np.zeros(M), np.cumsum(f, axis=0)])   # P[t, v] = sum of f[0:t, v]
    best, count = -np.inf, 0
    for j in range(min(S, K - 1, M - 1) + 1):
        values = np.array(list(combinations(range(M), j + 1)))   # strictly increasing values
        for cuts in combinations(range(1, K), j):               # positions where q increases
            bounds = (0, *cuts, K)
            total = np.zeros(len(values))
            for i in range(j + 1):
                # stage i covers points bounds[i] .. bounds[i+1]-1, all at value values[:, i]
                stage = P[bounds[i + 1]] - P[bounds[i]]
                total += stage[values[:, i]]
            best = max(best, float(total.max()))
            count += len(values)
    return best, count


def milp_best(f):
    """Exact optimum with no jump limit, as a 0-1 programme. x[k, v] = 1 if point k takes value v."""
    K, M = f.shape
    idx = lambda k, v: k * M + v

    # each point takes exactly one value
    rows = np.repeat(np.arange(K), M)
    cols = np.arange(K * M)
    A_one = coo_matrix((np.ones(K * M), (rows, cols)), shape=(K, K * M))

    # monotone: if point k+1 takes a value <= v, so does point k
    #   sum_{u<=v} x[k, u] - sum_{u<=v} x[k+1, u] >= 0
    r, c, d = [], [], []
    row = 0
    for k in range(K - 1):
        for v in range(M - 1):
            for u in range(v + 1):
                r += [row, row]
                c += [idx(k, u), idx(k + 1, u)]
                d += [1.0, -1.0]
            row += 1
    A_mono = coo_matrix((d, (r, c)), shape=(row, K * M))

    res = milp(
        c=-f.ravel(),                       # milp minimises
        constraints=[LinearConstraint(A_one, 1, 1), LinearConstraint(A_mono, 0, np.inf)],
        integrality=np.ones(K * M),
        bounds=(0, 1),
        options={"mip_rel_gap": 0},
    )
    if not res.success:
        raise RuntimeError(f"milp failed: {res.message}")
    return -res.fun


def path_ok(f, path, value, S):
    """The returned path is monotone, has at most S jumps, and earns the reported value."""
    steps = np.diff(path)
    earned = f[np.arange(len(path)), path].sum()
    return (
        np.all(steps >= 0)
        and (S is None or int(np.sum(steps > 0)) <= S)
        and abs(earned - value) <= TOL * max(1.0, abs(value))
    )


def close(a, b):
    return abs(a - b) <= TOL * max(1.0, abs(a), abs(b))


def main():
    failures = []
    if not random_cases():
        failures.append(("random cases", "mismatch"))

    data = pd.read_csv(CSV)
    for date, day in data.groupby("date"):
        t0 = time.time()
        f, info = build_points(day.sort_values("hour"), ALPHA, BETA, CAP)
        K, M = f.shape
        print(f"\n{date}: {K} points, {M} candidate values")

        # capped versions: DP vs enumeration
        dp = {}
        for S in range(S_MAX + 1):
            v_dp, path = solve(f, S)
            v_en, n = enumerate_best(f, S)
            dp[S] = v_dp
            ok = close(v_dp, v_en) and path_ok(f, path, v_dp, S)
            print(f"  at most {S} jump(s): DP {v_dp:10.4f}   enumeration {v_en:10.4f}"
                  f"   ({n:,} curves)   {'ok' if ok else 'MISMATCH'}")
            if not ok:
                failures.append((date, f"S={S}"))

        # unrestricted: DP vs integer programme
        v_dp, path = solve(f, None)
        v_ip = milp_best(f)
        ok = close(v_dp, v_ip) and path_ok(f, path, v_dp, None)
        print(f"  unrestricted:       DP {v_dp:10.4f}   integer prog {v_ip:10.4f}"
              f"   (DP path uses {int(np.sum(np.diff(path) > 0))} jumps)   {'ok' if ok else 'MISMATCH'}")
        if not ok:
            failures.append((date, "unrestricted"))

        # ordering
        v_sp, sp_path, _ = single_price(f)
        ok = (v_sp <= dp[1] + TOL and dp[1] <= v_dp + TOL
              and path_ok(f, sp_path, v_sp, 1))
        print(f"  single price {v_sp:.4f} <= at most 1 jump {dp[1]:.4f} <= unrestricted {v_dp:.4f}"
              f"   {'ok' if ok else 'FAILED'}   [{time.time() - t0:.0f}s]")
        if not ok:
            failures.append((date, "ordering"))

    print()
    if failures:
        print("FAILED:", failures)
        sys.exit(1)
    print(f"all checks passed ({N_RANDOM} random cases, {data['date'].nunique()} days)")


if __name__ == "__main__":
    main()
