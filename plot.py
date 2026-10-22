"""
plot.py — solve one day with the functions in build.py and compare three offers
in the price–quantity plane:
  left:   unrestricted (upper bound)
  middle: at most S_LIMITED jumps
  right:  single price (one flat offer, the usual baseline)

Each panel shows:
  grey bars  the hour's window [alpha*Q_h, Q_h], drawn at the point's price
  dots       each point's q (blue = real-time point, orange = day-ahead point;
             hollow = negative coefficient, i.e. the point prefers to clear less)
  dark line  the offer curve b(q)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from build import build_points, solve, single_price

CSV = "caiso_sp15.csv"
DATE = None              # None = first day in the file
ALPHA, BETA, CAP = 0.9, 0.05, 6.0
S_LIMITED = 1            # jumps allowed in the middle panel

# colours: two categories plus text and helper elements
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#898781"
WINDOW, GRID, SURFACE = "#d3d1c7", "#e1e0d9", "#fcfcfb"


def staircase(price, q, cap):
    """Staircase through every (q_k, p_k): flat parts stop at each point, vertical parts rise between prices."""
    xs, ys = [0.0], [price[0]]
    for k in range(len(price)):
        xs.append(q[k]); ys.append(price[k])          # flat to q_k
        if k + 1 < len(price):
            xs.append(q[k]); ys.append(price[k + 1])  # up to the next price
    top = price[-1] + 0.08 * (price[-1] - price[0] + 1)
    xs += [q[-1], cap]; ys += [top, top]              # above the last point, offer higher than every price
    return xs, ys


def draw(ax, day, info, q_pts, curve, title):
    """q_pts: q of each merged point; curve: (xs, ys) of the offer curve."""
    p_d, p_r = day["p_d"].to_numpy(float), day["p_r"].to_numpy(float)
    Q = info["Q"]

    # windows: one grey bar per original point
    for g, p in zip(info["groups"], info["price"]):
        for i in g:
            h = info["hour"][i]
            ax.hlines(p, ALPHA * Q[h], Q[h], color=WINDOW, lw=5, zorder=1)

    # offer curve
    ax.plot(*curve, color=INK_2, lw=2, zorder=2)

    # points: colour = real-time / day-ahead, hollow = negative coefficient
    for g, p, qk in zip(info["groups"], info["price"], q_pts):
        for i in g:
            h, kind = info["hour"][i], info["kind"][i]
            coef = BETA * p_r[h] if kind == "r" else p_d[h] - p_r[h]
            color = BLUE if kind == "r" else ORANGE
            ax.scatter(qk, p, s=46, zorder=3,
                       facecolor=color if coef >= 0 else SURFACE,
                       edgecolor=color, linewidth=2)

    ax.set_title(title, color=INK, fontsize=11, loc="left")
    ax.set_xlim(-0.1, CAP * 1.03)
    ax.set_xlabel("Output q (MW)", color=INK_2)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.tick_params(colors=MUTED)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.set_facecolor(SURFACE)


def main():
    data = pd.read_csv(CSV)
    date = DATE or data["date"].iloc[0]
    day = data[data["date"] == date].sort_values("hour")
    f, info = build_points(day, ALPHA, BETA, CAP)
    price, cand, const = info["price"], info["cand"], info["const"]

    # three offers
    best_free, path_free = solve(f, None)
    best_lim, path_lim = solve(f, S_LIMITED)
    best_one, path_one, k = single_price(f)

    q_free, q_lim = cand[path_free], cand[path_lim]
    # single price: points below b clear nothing (drawn at q = 0), points at or above b clear fully
    q_one = np.where(path_one == 0, 0.0, cand[path_one])
    b = price[k] if k < len(price) else price[-1] + 0.08 * (price[-1] - price[0] + 1)

    jumps = "jump" if S_LIMITED == 1 else "jumps"
    panels = [
        (q_free, staircase(price, q_free, CAP), "Unrestricted (upper bound)", best_free),
        (q_lim, staircase(price, q_lim, CAP), f"At most {S_LIMITED} {jumps}", best_lim),
        (q_one, ([0, CAP], [b, b]), f"Single price b = {b:.1f}", best_one),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(18, 6), sharey=True, facecolor=SURFACE)
    for ax, (q_pts, curve, name, best) in zip(axes, panels):
        draw(ax, day, info, q_pts, curve,
             f"{name}\nOffer-dependent revenue {best:.1f}, total {best + const:.1f}")
    axes[0].set_ylabel("Price p ($/MWh)", color=INK_2)

    legend = [
        Line2D([], [], marker="o", ls="", color=BLUE, markersize=8, label="Real-time point (price p_r)"),
        Line2D([], [], marker="o", ls="", color=ORANGE, markersize=8, label="Day-ahead point (price p_d)"),
        Line2D([], [], marker="o", ls="", markerfacecolor=SURFACE, markeredgecolor=MUTED,
               markeredgewidth=2, markersize=8, label="Hollow: negative coefficient, prefers to clear less"),
        Line2D([], [], color=WINDOW, lw=5, label="Hour's window [αQ, Q]"),
        Line2D([], [], color=INK_2, lw=2, label="Offer curve b(q)"),
    ]
    fig.legend(handles=legend, loc="upper center", ncol=5, frameon=False,
               bbox_to_anchor=(0.5, 1.0), fontsize=10, labelcolor=INK_2)
    fig.suptitle(f"{date}   α = {ALPHA}, β = {BETA}, plant {CAP} MW",
                 x=0.01, y=0.93, ha="left", color=INK, fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.9))

    print(f"{date}  total revenue: unrestricted {best_free + const:.2f}, "
          f"at most {S_LIMITED} {jumps} {best_lim + const:.2f}, single price {best_one + const:.2f}")

    out = f"pq_{date}.png"
    fig.savefig(out, dpi=150, facecolor=SURFACE)
    print(f"saved {out}")
    plt.show()


if __name__ == "__main__":
    main()
