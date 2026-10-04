"""Render the README / portfolio charts from data/processed/ into images/."""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC, IMG = ROOT / "data/processed", ROOT / "images"
IMG.mkdir(exist_ok=True)

SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, RED, NEUTRAL = "#2a78d6", "#eb6834", "#e34948", "#b9b8b2"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "Segoe UI", "font.size": 11, "text.color": INK,
    "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "axes.titlesize": 15, "axes.titleweight": "bold", "axes.titlelocation": "left",
})


def subtitle(ax, text):
    ax.text(0, 1.02, text, transform=ax.transAxes, color=INK_2, fontsize=10.5, va="bottom")


def footnote(fig, text="Data: Cricsheet ball-by-ball (IPL 2025), Wikipedia auction prices. Runs added vs. league average."):
    fig.text(0.01, 0.01, text, color=INK_2, fontsize=8.5)


def save(fig, name):
    fig.savefig(IMG / name, dpi=200, bbox_inches="tight")
    plt.close(fig)


v = pd.read_csv(PROC / "value_2025_w6.csv")
played = v[v.matches > 0]

# 1 ── price vs impact scatter ───────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(11, 6.5))
steals, busts = v.nlargest(6, "surplus"), v.nsmallest(6, "surplus")
rest = played[~played.index.isin(steals.index.union(busts.index))]
ax.scatter(rest.price_cr, rest.total_runs_added, s=40, color=NEUTRAL, edgecolor=SURFACE, linewidth=1.5, zorder=2)
ax.scatter(steals.price_cr, steals.total_runs_added, s=70, color=BLUE, edgecolor=SURFACE, linewidth=2, zorder=3, label="Biggest steals")
ax.scatter(busts.price_cr, busts.total_runs_added, s=70, color=RED, edgecolor=SURFACE, linewidth=2, zorder=3, label="Biggest busts")
x = np.linspace(0, v.price_cr.max(), 50)
ax.plot(x, v.expected_runs_added.iloc[0] + (x - v.price_cr.iloc[0]) *
        np.polyfit(v.price_cr, v.expected_runs_added, 1)[0], color=INK_2, lw=1.5, ls="--", zorder=1)
ax.text(26.5, np.polyval(np.polyfit(v.price_cr, v.expected_runs_added, 1), 26.5) + 8, "fair-price line",
        color=INK_2, fontsize=9.5, ha="right")
ax.axhline(0, color=INK_2, lw=0.8)
for _, r in pd.concat([steals, busts]).iterrows():
    ax.annotate(r.player_full, (r.price_cr, r.total_runs_added), xytext=(7, 4), textcoords="offset points",
                fontsize=9.5, color=INK)
ax.set_xlabel("Price paid (₹ crore)")
ax.set_ylabel("Runs added vs. average player")
ax.set_title("Price barely predicts performance", pad=28)
subtitle(ax, f"Each dot is a player bought or retained for IPL 2025 (r = {v.price_cr.corr(v.total_runs_added):.2f}). "
             "Above the line = more impact than the price implied.")
ax.legend(frameon=False, loc="upper left", labelcolor=INK)
footnote(fig)
save(fig, "01_price_vs_impact.png")

# 2 ── top steals and busts ───────────────────────────────────────────────────
top = pd.concat([v.nlargest(10, "surplus"), v.nsmallest(10, "surplus").iloc[::-1]])
fig, ax = plt.subplots(figsize=(10, 8))
colors = [BLUE if s > 0 else RED for s in top.surplus]
y = np.arange(len(top))[::-1]
ax.barh(y, top.surplus, color=colors, height=0.7, edgecolor=SURFACE, linewidth=2)
for yi, (_, r) in zip(y, top.iterrows()):
    label = f"{r.player_full}  ·  ₹{r.price_cr:g} cr"
    ax.text(-3 if r.surplus > 0 else 3, yi, label, va="center", ha="right" if r.surplus > 0 else "left", fontsize=9.5)
    ax.text(r.surplus + (3 if r.surplus > 0 else -3), yi, f"{r.surplus:+.0f}", va="center",
            ha="left" if r.surplus > 0 else "right", fontsize=9, color=INK_2)
ax.set_yticks([])
ax.axvline(0, color=INK_2, lw=0.8)
ax.grid(axis="y", visible=False)
ax.set_xlim(-160, 190)
ax.set_xlabel("Runs added beyond what the price predicted")
ax.set_title("The 10 best and worst buys of IPL 2025", pad=28)
subtitle(ax, "Blue = delivered more than the price tag implied; red = delivered less.")
footnote(fig)
save(fig, "02_steals_and_busts.png")

# 3 ── what each price band delivered ─────────────────────────────────────────
order = ["Budget (<₹3cr)", "Mid (₹3-10cr)", "Marquee (₹10cr+)"]
g = v.groupby("price_band").agg(n=("price_cr", "size"), spend=("price_cr", "sum"),
                                dnp=("matches", lambda s: (s == 0).mean() * 100),
                                ).reindex(order)
g["hit"] = played.groupby("price_band").total_runs_added.apply(lambda s: (s > 0).mean() * 100).reindex(order)
fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
for ax, col, title, color in ((axes[0], "dnp", "Never played a match", NEUTRAL),
                              (axes[1], "hit", "Beat an average player (of those who played)", BLUE)):
    bars = ax.bar(range(3), g[col], color=color, width=0.6, edgecolor=SURFACE, linewidth=2)
    ax.bar_label(bars, labels=[f"{x:.0f}%" for x in g[col]], padding=4, fontsize=11, color=INK)
    ax.set_xticks(range(3), [f"{b}\n{n} players" for b, n in zip(order, g.n)], fontsize=9.5)
    ax.set_ylim(0, 100)
    ax.set_yticks([])
    ax.grid(False)
    ax.set_title(title, fontsize=12.5)
fig.suptitle("Cheap buys are lottery tickets: a third never got a game", x=0.01, ha="left",
             fontsize=15, fontweight="bold", y=1.04)
fig.text(0.01, -0.06, "Share of players in each price band. Data: Cricsheet, Wikipedia (IPL 2025).", color=INK_2, fontsize=8.5)
save(fig, "03_price_bands.png")

# 4 ── metric validation: team runs added vs win % ────────────────────────────
t = pd.read_csv(PROC / "team_validation.csv")
fig, ax = plt.subplots(figsize=(9, 6))
old, new = t[t.season != 2025], t[t.season == 2025]
ax.scatter(old.runs_added, old.win_pct * 100, s=36, color=NEUTRAL, edgecolor=SURFACE, linewidth=1.5, label="2015–2026 team-seasons")
ax.scatter(new.runs_added, new.win_pct * 100, s=70, color=BLUE, edgecolor=SURFACE, linewidth=2, label="2025 teams", zorder=3)
ABBR = {"Chennai Super Kings": "CSK", "Delhi Capitals": "DC", "Gujarat Titans": "GT", "Kolkata Knight Riders": "KKR",
        "Lucknow Super Giants": "LSG", "Mumbai Indians": "MI", "Punjab Kings": "PBKS", "Rajasthan Royals": "RR",
        "Royal Challengers Bengaluru": "RCB", "Sunrisers Hyderabad": "SRH"}
NUDGE = {"CSK": (7, -14), "KKR": (7, -10)}  # teams that finished almost level
for _, r in new.iterrows():
    ax.annotate(ABBR[r.team], (r.runs_added, r.win_pct * 100), xytext=NUDGE.get(ABBR[r.team], (7, 3)),
                textcoords="offset points", fontsize=9.5)
ax.set_xlabel("Team total runs added (all players)")
ax.set_ylabel("Win %")
ax.set_title("Sanity check: the metric tracks winning", pad=28)
subtitle(ax, f"Correlation r = {t.win_pct.corr(t.runs_added):.2f} across {len(t)} team-seasons. "
             "2025's top four by runs added were the four playoff teams.")
ax.legend(frameon=False, loc="upper left", labelcolor=INK)
footnote(fig, "Data: Cricsheet ball-by-ball and match results, IPL 2015–2026.")
save(fig, "04_metric_validation.png")

# 5 ── persistence: 2025 vs 2026 ──────────────────────────────────────────────
p = pd.read_csv(PROC / "persistence.csv")
q = p.groupby("quintile_2025")[["ra_per_match_2025", "ra_per_match_2026"]].mean()
fig, ax = plt.subplots(figsize=(10, 5.5))
xs, w = np.arange(5), 0.36
b1 = ax.bar(xs - w / 2 - 0.01, q.ra_per_match_2025, w, color=BLUE, label="2025", edgecolor=SURFACE, linewidth=2)
b2 = ax.bar(xs + w / 2 + 0.01, q.ra_per_match_2026, w, color=ORANGE, label="2026 (next season)", edgecolor=SURFACE, linewidth=2)
ax.bar_label(b1, fmt="%+.1f", padding=3, fontsize=9)
ax.bar_label(b2, fmt="%+.1f", padding=3, fontsize=9)
ax.axhline(0, color=INK_2, lw=0.8)
ax.set_xticks(xs, ["Worst 20%", "2nd", "Middle", "4th", "Best 20%"])
ax.set_xlabel("Players grouped by their 2025 performance")
ax.set_ylabel("Runs added per match")
ax.set_title("Last season's heroes come back to earth", pad=28)
subtitle(ax, f"{len(p)} players with 7+ matches in both seasons. Year-to-year correlation r = "
             f"{p.ra_per_match_2025.corr(p.ra_per_match_2026):.2f}: one great season is mostly noise.")
ax.legend(frameon=False, labelcolor=INK)
footnote(fig, "Data: Cricsheet ball-by-ball, IPL 2025–2026.")
save(fig, "05_regression_to_mean.png")
print("charts written to", IMG)
