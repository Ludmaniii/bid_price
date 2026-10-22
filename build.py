"""
build.py — turn one day of 24 hourly rows into the matrix f for the dynamic programme, then solve.

Notation follows the README:
  each hour h has the window [alpha*Q_h, Q_h], of length w_h = (1-alpha)*Q_h
  each hour has two points:
    real-time point: price p_r, coefficient beta * p_r
    day-ahead point: price p_d, coefficient p_d - p_r
  f[k, j] = coefficient_k * clip(candidate_j - alpha*Q_h, 0, w_h)
  total revenue = constant + optimal value of the DP
  constant = sum_h (1-beta) * p_r * w_h, independent of the offer
"""

import numpy as np
import pandas as pd


def build_points(day, alpha=0.9, beta=0.05, capacity=6.0):
    """
    day: DataFrame for one day, 24 rows, with columns p_d, p_r, solar
    returns f (sorted by price, equal prices merged) and an info dict
    """
    p_d = day["p_d"].to_numpy(float)
    p_r = day["p_r"].to_numpy(float)
    # night-time solar can be slightly negative; clip at 0
    solar = np.clip(day["solar"].to_numpy(float), 0, None)

    # rescale system solar output to one plant, keeping the daily shape
    Q = solar / solar.max() * capacity if solar.max() > 0 else np.zeros_like(solar)
    Q[Q < 1e-6 * capacity] = 0.0   # treat numerically tiny output as zero
    lo = alpha * Q            # left end of the window
    w = (1 - alpha) * Q       # window length

    # hours with Q = 0 have an empty window and do not affect revenue
    hrs = np.flatnonzero(Q > 0)

    # two points per hour: real-time first, then day-ahead
    price = np.concatenate([p_r[hrs], p_d[hrs]])
    coef = np.concatenate([beta * p_r[hrs], (p_d - p_r)[hrs]])
    hour = np.concatenate([hrs, hrs])
    kind = np.array(["r"] * len(hrs) + ["d"] * len(hrs))

    # candidate values: both ends of every window, deduplicated and sorted
    cand = np.unique(np.concatenate([lo[hrs], Q[hrs]]))

    # f[k, j] = coefficient × clipped length
    L = np.clip(cand[None, :] - lo[hour][:, None], 0, w[hour][:, None])
    f = coef[:, None] * L

    # sort by price, low to high
    order = np.argsort(price, kind="stable")
    price, coef, hour, kind, f = price[order], coef[order], hour[order], kind[order], f[order]

    # points with exactly equal prices must share one q: merge them and add their f
    uniq_price, start = np.unique(price, return_index=True)
    f_merged = np.add.reduceat(f, start, axis=0) if len(price) else f
    groups = np.split(np.arange(len(price)), start[1:]) if len(price) else []

    info = {
        "price": uniq_price,     # price of each merged point
        "groups": groups,        # which original points each merged point contains
        "hour": hour,            # hour of each original point
        "kind": kind,            # "r" = real-time point, "d" = day-ahead point
        "cand": cand,            # candidate values
        "Q": Q,
        "const": float(np.sum((1 - beta) * p_r * w)),
    }
    return f_merged, info


def solve(f, S=None):
    """Dynamic programme. S = maximum number of jumps; None means no limit."""
    K, M = f.shape
    if K == 0:
        return 0.0, np.array([], dtype=int)
    if S is None:
        S = K - 1

    V = np.full((K, M, S + 1), -np.inf)
    arrow = np.full((K, M, S + 1, 2), -1, dtype=int)
    V[0, :, 0] = f[0]

    for k in range(1, K):
        for v in range(M):
            for s in range(S + 1):
                stay = V[k-1, v, s]
                if v > 0 and s > 0:
                    u = int(np.argmax(V[k-1, :v, s-1]))
                    jump = V[k-1, u, s-1]
                else:
                    u, jump = -1, -np.inf
                if stay >= jump:
                    V[k, v, s] = f[k, v] + stay
                    arrow[k, v, s] = [v, s]
                else:
                    V[k, v, s] = f[k, v] + jump
                    arrow[k, v, s] = [u, s - 1]

    v, s = np.unravel_index(np.argmax(V[K-1]), V[K-1].shape)
    best = float(V[K-1, v, s])
    path = [v]
    for k in range(K - 1, 0, -1):
        v, s = arrow[k, v, s]
        path.append(v)
    path.reverse()
    return best, np.array(path)


def single_price(f):
    """
    Single price: every MW is offered at the same price b, i.e. a flat curve.
    Points priced below b clear nothing (column 0); points at or above b clear fully (last column).
    Try every jump position k (the first k points clear nothing) and keep the best.
    Returns (revenue, path, k).
    """
    K, M = f.shape
    if K == 0:
        return 0.0, np.array([], dtype=int), 0
    low, high = f[:, 0], f[:, -1]
    totals = [low[:k].sum() + high[k:].sum() for k in range(K + 1)]
    k = int(np.argmax(totals))
    path = np.array([0] * k + [M - 1] * (K - k))
    return float(totals[k]), path, k


def main(csv="caiso_sp15.csv", date=None, alpha=0.9, beta=0.05, capacity=6.0):
    data = pd.read_csv(csv)
    date = date or data["date"].iloc[0]
    day = data[data["date"] == date].sort_values("hour")

    f, info = build_points(day, alpha, beta, capacity)
    print(f"{date}: {f.shape[0]} points (equal prices merged), {f.shape[1]} candidate values")

    for S in [None, 1, 2]:
        best, path = solve(f, S)
        label = "unrestricted" if S is None else f"at most {S} jump{'s' if S > 1 else ''}"
        print(f"{label}: offer-dependent {best:.2f}, total {best + info['const']:.2f}")

    # optimal points (p_k, q_k) without a jump limit
    best, path = solve(f, None)
    q = info["cand"][path]
    print("\noptimal points (sorted by price):")
    for p, qk in zip(info["price"], q):
        print(f"  p = {p:9.2f}   q = {qk:.3f}")


if __name__ == "__main__":
    main()
