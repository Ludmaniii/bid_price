"""
make_figures.py — generate the three figures used in the docs, in English and Chinese, into figures/.
  English: fig1_setup.png, fig2_window.png, fig3_dp_paths.png         (used by README.md)
  Chinese: fig1_setup_zh.png, fig2_window_zh.png, fig3_dp_paths_zh.png (used by derivation.zh.md)
Run: python make_figures.py
"""

import os

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures")
os.makedirs(OUT, exist_ok=True)

BLUE, ORANGE, AQUA, VIOLET = "#2a78d6", "#eb6834", "#1baf7a", "#6250d6"
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRAY_FILL, GRID, SURFACE = "#d3d1c7", "#e1e0d9", "#fcfcfb"

plt.rcParams.update({
    "font.sans-serif": ["Noto Sans CJK SC", "Microsoft YaHei", "SimHei", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": GRID,
    "axes.labelcolor": INK_2,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "text.color": INK,
})

# All text labels. Math ($...$) only appears in pure-math strings: mixing CJK text with mathtext drops glyphs.
T = {
    "en": {
        "a_title": "(a) Two prices per hour",
        "pd": "Day-ahead p_d", "pr": "Real-time p_r",
        "hour": "Hour h", "price": "Price ($/MWh)",
        "b_title": "(b) One hour: revenue vs offer (p_d < p_r)",
        "both": "Cleared in both: p_d", "rt_only": "Real-time only: p_r",
        "none": "Neither: (1−β)·p_r",
        "offer": "Offer b", "rev": "Revenue per MWh  r_h(b)",
        "c_title": "(c) One monotone curve for all hours",
        "hours": ["17:00", "9:00", "12:00"],
        "q": "Output q (MW)", "bq": "Offer b(q)",
        "left": "Left: L = 0, nothing clears at this price",
        "mid": "Inside: L = b⁻¹(p) − αQ_h, partly clears",
        "right": "Right: L = (1−α)Q_h, all clears",
        "seg_both": "Cleared in both\npaid p_d",
        "seg_rt": "Real-time only\npaid p_r",
        "seg_da": "Day-ahead only\np_d − β·p_r",
        "seg_none": "Neither\n(1−β)·p_r",
        "path_a": "Path A: (q₁, q₂, q₃) = (1, 1, 3)",
        "path_b": "Path B: (q₁, q₂, q₃) = (1, 3, 3)",
        "path_sub": "Revenue = {}, one jump",
        "point": "Point {}",
        "suffix": "",
    },
    "zh": {
        "a_title": "(a) 每个小时两个价格",
        "pd": "日前价 p_d", "pr": "实时价 p_r",
        "hour": "小时 h", "price": "价格 ($/MWh)",
        "b_title": "(b) 单个小时：收益对报价是阶梯（此例 p_d < p_r）",
        "both": "两边都中：p_d", "rt_only": "只中实时：p_r",
        "none": "都不中：(1−β)·p_r",
        "offer": "报价 b", "rev": "每 MWh 收益 r_h(b)",
        "c_title": "(c) 一条单调曲线，24 小时共用",
        "hours": ["17 点", "9 点", "12 点"],
        "q": "出力 q (MW)", "bq": "报价 b(q)",
        "left": "左边：L = 0，这个价格上一点都不中",
        "mid": "中间：L = b⁻¹(p) − αQ_h，部分中标",
        "right": "右边：L = (1−α)Q_h，全中",
        "seg_both": "两边都中\n按 p_d",
        "seg_rt": "只中实时\n按 p_r",
        "seg_da": "只中日前\np_d − β·p_r",
        "seg_none": "都不中\n(1−β)·p_r",
        "path_a": "路径 A：(q₁, q₂, q₃) = (1, 1, 3)",
        "path_b": "路径 B：(q₁, q₂, q₃) = (1, 3, 3)",
        "path_sub": "收益 = {}，跳变 1 次",
        "point": "点 {}",
        "suffix": "_zh",
    },
}


def clean(ax, grid_y=True):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    if grid_y:
        ax.grid(axis="y", color=GRID, lw=0.8)
        ax.set_axisbelow(True)


# ---------------------------------------------------------------- figure 1: what the problem looks like
def fig_setup(t):
    h = np.arange(24)
    sun = np.clip(np.sin((h - 6) / 12 * np.pi), 0, None)
    rng = np.random.default_rng(3)
    p_d = 60 - 70 * sun + 120 * np.exp(-((h - 19) / 2) ** 2) + rng.normal(0, 8, 24)
    p_r = p_d + rng.normal(0, 30, 24)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))

    # (a) the two prices over the day
    ax = axes[0]
    hh = np.append(h, 24)
    ax.step(hh, np.append(p_d, p_d[-1]), where="post", color=BLUE, lw=2, label=t["pd"])
    ax.step(hh, np.append(p_r, p_r[-1]), where="post", color=ORANGE, lw=2, label=t["pr"])
    ax.set_xlim(0, 24); ax.set_xticks(range(0, 25, 6))
    ax.set_xlabel(t["hour"]); ax.set_ylabel(t["price"])
    ax.set_title(t["a_title"], loc="left", fontsize=11)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    clean(ax)

    # (b) one hour: revenue per MWh is a three-level step function of the offer b
    ax = axes[1]
    beta, pd_, pr_ = 0.05, 40.0, 80.0
    b = np.linspace(0, 120, 1201)
    r = (1 - beta) * pr_ + beta * pr_ * (b <= pr_) + (pd_ - pr_) * (b <= pd_)
    ax.plot(b, r, color=VIOLET, lw=2, drawstyle="steps-post")
    for x, name in [(pd_, "$p_d$"), (pr_, "$p_r$")]:
        ax.axvline(x, color=MUTED, lw=0.8, ls=":")
        ax.text(x, 33, name, ha="center", va="bottom", color=INK_2)
    ax.text(18, pd_ + 2, t["both"], ha="center", fontsize=9, color=INK_2)
    ax.text(60, pr_ + 2, t["rt_only"], ha="center", fontsize=9, color=INK_2)
    ax.text(101, (1 - beta) * pr_ - 6, t["none"], ha="center", fontsize=9, color=INK_2)
    ax.set_ylim(30, 90); ax.set_xlim(0, 120)
    ax.set_xlabel(t["offer"]); ax.set_ylabel(t["rev"])
    ax.set_title(t["b_title"], loc="left", fontsize=11)
    clean(ax)

    # (c) one offer curve for all 24 hours; each hour reads only its window
    ax = axes[2]
    curve_q = [0, 1.5, 3, 4.5, 6]
    curve_p = [-20, 20, 60, 120, 250]
    for q_h, lab in zip([1.2, 2.6, 5.4], t["hours"]):
        ax.axvspan(0.9 * q_h, q_h, color=GRAY_FILL, alpha=0.8, lw=0)
        ax.text(0.95 * q_h, 262, lab, ha="center", fontsize=9, color=INK_2)
    ax.plot(curve_q, curve_p, color=VIOLET, lw=2, marker="o", ms=5)
    ax.set_xlim(0, 6.2); ax.set_ylim(-40, 280)
    ax.set_xlabel(t["q"]); ax.set_ylabel(t["bq"])
    ax.set_title(t["c_title"], loc="left", fontsize=11)
    clean(ax)

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, f"fig1_setup{t['suffix']}.png"), dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- figure 2: clipping and settlement inside the window
def bar(ax, y, x0, x1, color, text, text_color=INK, h=0.5):
    ax.add_patch(Rectangle((x0, y - h / 2), x1 - x0, h, facecolor=color, edgecolor=SURFACE, lw=2))
    if text:
        ax.text((x0 + x1) / 2, y, text, ha="center", va="center", fontsize=9.5, color=text_color)


def fig_window(t):
    fig, axes = plt.subplots(2, 1, figsize=(11, 6.6), gridspec_kw={"height_ratios": [3, 2.4]})

    # top: three positions of b^{-1}(p) relative to the window
    ax = axes[0]
    lo, hi = 4.0, 8.0
    for i, (x, key) in enumerate([(2.2, "left"), (5.6, "mid"), (9.3, "right")]):
        y = 2 - i
        ax.plot([0, 10.5], [y, y], color=GRID, lw=1, zorder=0)
        bar(ax, y, lo, hi, GRAY_FILL, "", h=0.32)
        L1 = min(max(x, lo), hi)
        if L1 > lo:
            bar(ax, y, lo, L1, BLUE, "L", text_color="#ffffff", h=0.32)
        ax.plot([x, x], [y - 0.28, y + 0.28], color=INK, lw=2)
        ax.text(x, y + 0.32, "$b^{-1}(p)$", ha="center", va="bottom", fontsize=9.5)
        ax.text(10.7, y, t[key], va="center", fontsize=10, color=INK_2)
    for x, lab in [(lo, "$\\alpha Q_h$"), (hi, "$Q_h$")]:
        ax.text(x, -0.62, lab, ha="center", va="top", fontsize=10, color=INK_2)
    ax.text(0, 2.75, "$L(p)=\\min(\\max(b^{-1}(p)-\\alpha Q_h,\\,0),\\,(1-\\alpha)Q_h)$",
            fontsize=11.5, va="bottom")
    ax.set_xlim(-0.2, 21); ax.set_ylim(-1.0, 3.3); ax.axis("off")

    # bottom: the window split by settlement, for both price orders
    ax = axes[1]
    w0, w1 = 0.0, 10.0
    qd, qr = 3.0, 6.5                     # p_d < p_r implies q_d <= q_r
    y = 1.0
    bar(ax, y, w0, qd, BLUE, t["seg_both"], "#ffffff")
    bar(ax, y, qd, qr, AQUA, t["seg_rt"])
    bar(ax, y, qr, w1, GRAY_FILL, t["seg_none"])
    ax.text(-0.3, y, "$p_d < p_r$", ha="right", va="center", fontsize=11)
    for x, lab in [(qd, "$q_d=b^{-1}(p_d)$"), (qr, "$q_r=b^{-1}(p_r)$")]:
        ax.text(x, y + 0.33, lab, ha="center", va="bottom", fontsize=9, color=INK_2)
    qr, qd = 3.0, 6.5                     # p_d > p_r implies q_r <= q_d
    y = 0.0
    bar(ax, y, w0, qr, BLUE, t["seg_both"], "#ffffff")
    bar(ax, y, qr, qd, ORANGE, t["seg_da"], "#ffffff")
    bar(ax, y, qd, w1, GRAY_FILL, t["seg_none"])
    ax.text(-0.3, y, "$p_d > p_r$", ha="right", va="center", fontsize=11)
    for x, lab in [(qr, "$q_r$"), (qd, "$q_d$")]:
        ax.text(x, y + 0.33, lab, ha="center", va="bottom", fontsize=9, color=INK_2)
    ax.text(w0, -0.5, "$\\alpha Q_h$", ha="center", va="top", fontsize=10, color=INK_2)
    ax.text(w1, -0.5, "$Q_h$", ha="center", va="top", fontsize=10, color=INK_2)
    ax.set_xlim(-2.2, 21); ax.set_ylim(-0.85, 1.65); ax.axis("off")

    fig.tight_layout()
    fig.savefig(os.path.join(OUT, f"fig2_window{t['suffix']}.png"), dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------- figure 3: the two optimal paths in the example
def fig_dp_path(t):
    f = np.array([[3, 0, 0], [0, 2, 0], [0, 0, 4]])   # f[k, v]
    paths = [((0, 0, 2), t["path_a"]), ((0, 2, 2), t["path_b"])]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    for ax, (path, title) in zip(axes, paths):
        for k in range(3):
            for v in range(3):
                on = path[k] == v
                ax.add_patch(Rectangle((k, 2 - v), 1, 1, facecolor=BLUE if on else SURFACE,
                                       edgecolor=GRID, lw=1.5))
                ax.text(k + 0.5, 2 - v + 0.5, f[k, v], ha="center", va="center", fontsize=15,
                        color="#ffffff" if on else INK_2)
        for k in range(2):
            a = (k + 0.5, 2 - path[k] + 0.5)
            b = (k + 1.5, 2 - path[k + 1] + 0.5)
            ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=14,
                                         color=ORANGE, lw=2, shrinkA=16, shrinkB=16))
        total = sum(f[k, path[k]] for k in range(3))
        ax.set_title(f"{title}\n{t['path_sub'].format(total)}", fontsize=11, loc="left")
        ax.set_xticks([0.5, 1.5, 2.5], [t["point"].format(i) for i in (1, 2, 3)])
        ax.set_yticks([2.5, 1.5, 0.5], ["v = 1", "v = 2", "v = 3"])
        ax.set_xlim(0, 3); ax.set_ylim(0, 3); ax.set_aspect("equal")
        ax.tick_params(length=0)
        for s in ax.spines.values():
            s.set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, f"fig3_dp_paths{t['suffix']}.png"), dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    for lang in ("en", "zh"):
        fig_setup(T[lang])
        fig_window(T[lang])
        fig_dp_path(T[lang])
    print("saved to", OUT)
