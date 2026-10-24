"""
results.py — solve every day in caiso_sp15.csv under three offer formats and summarise.

Revenue is the revenue earned on the offer-dependent window [alpha*Q_h, Q_h] of each hour
(the share alpha of output that clears unconditionally is the same for every offer and is left out).

Writes results/summary.csv and prints a Markdown table for the README.
Run fetch.py first to create caiso_sp15.csv.
"""

import os

import numpy as np
import pandas as pd

from build import build_points, single_price, solve

CSV = "caiso_sp15.csv"
OUT = os.path.join("results", "summary.csv")
ALPHA, BETA, CAP = 0.9, 0.05, 6.0


def main():
    data = pd.read_csv(CSV)
    rows = []
    for date, day in data.groupby("date"):
        f, info = build_points(day.sort_values("hour"), ALPHA, BETA, CAP)
        c = info["const"]
        v_sp, _, _ = single_price(f)
        v_1, _ = solve(f, 1)
        v_free, path = solve(f, None)
        rows.append({
            "date": date,
            "single_price": c + v_sp,
            "at_most_1_jump": c + v_1,
            "unrestricted": c + v_free,
            "jumps_used": int(np.sum(np.diff(path) > 0)),
        })

    df = pd.DataFrame(rows)
    df["gain_vs_single"] = df["unrestricted"] - df["single_price"]
    df["gain_pct"] = 100 * df["gain_vs_single"] / df["single_price"]

    os.makedirs("results", exist_ok=True)
    df.round(4).to_csv(OUT, index=False)

    tot = df[["single_price", "at_most_1_jump", "unrestricted"]].sum()
    gap = tot["unrestricted"] - tot["single_price"]
    print("| Day | Single price | At most 1 jump | Unrestricted | Jumps used | Gain over single price |")
    print("|---|---:|---:|---:|---:|---:|")
    for r in df.itertuples():
        print(f"| {r.date} | {r.single_price:.2f} | {r.at_most_1_jump:.2f} | {r.unrestricted:.2f} "
              f"| {r.jumps_used} | {r.gain_vs_single:.2f} ({r.gain_pct:.2f}%) |")
    print(f"| **Week** | **{tot['single_price']:.2f}** | **{tot['at_most_1_jump']:.2f}** "
          f"| **{tot['unrestricted']:.2f}** | | **{gap:.2f} ({100 * gap / tot['single_price']:.2f}%)** |")
    share = (tot["at_most_1_jump"] - tot["single_price"]) / gap if gap > 0 else float("nan")
    print(f"\none jump closes {100 * share:.0f}% of the gap between single price and unrestricted")
    print(f"single price is already optimal on {int((df['gain_vs_single'] < 1e-9).sum())} of {len(df)} days")
    print(f"saved {OUT}")


if __name__ == "__main__":
    main()
