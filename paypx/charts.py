"""Charts: EPL vs La Liga pay-index comparison, broad and granular levels.

Uses a headless matplotlib backend so it renders in any environment. Colours
follow a small, colour-blind-safe categorical palette; light background, one
colour per league, value labels on bars, and high-spread positions marked.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from . import positions, config  # noqa: E402

# Colour-blind-safe two-league palette (Okabe-Ito subset).
_LEAGUE_COLOR = {"epl": "#0072B2", "laliga": "#D55E00"}
_LEAGUE_LABEL = {"epl": "Premier League", "laliga": "La Liga"}

_ORDER = {
    "broad": positions.BROAD,
    "granular": positions.GRANULAR,
}


def _ordered_positions(table, level: str) -> list[str]:
    present = list(table["position"].unique())
    order = _ORDER[level]
    return [p for p in order if p in present] + [
        p for p in present if p not in order
    ]


def comparison_chart(table, level: str, out_path=None, season: str = ""):
    """Grouped bar chart: mean index by position, one bar-group per league.

    ``table`` is the aggregate() output filtered to one level but possibly
    multiple leagues. Median line at 1.00 is drawn for reference.
    """
    positions_order = _ordered_positions(table, level)
    leagues = list(table["league"].unique())
    n_groups = len(positions_order)
    n_leagues = max(len(leagues), 1)
    bar_w = 0.8 / n_leagues

    fig, ax = plt.subplots(figsize=(max(7, n_groups * 1.15), 4.8))
    x = list(range(n_groups))

    for li, lg in enumerate(leagues):
        sub = table[table["league"] == lg].set_index("position")
        vals, flags = [], []
        for p in positions_order:
            if p in sub.index:
                vals.append(float(sub.loc[p, "mean_index"]))
                flags.append(bool(sub.loc[p, "high_spread"]))
            else:
                vals.append(0.0)
                flags.append(False)
        offs = [xi + (li - (n_leagues - 1) / 2) * bar_w for xi in x]
        bars = ax.bar(offs, vals, width=bar_w * 0.95,
                      color=_LEAGUE_COLOR.get(lg, f"C{li}"),
                      label=_LEAGUE_LABEL.get(lg, lg))
        for rect, val, flag in zip(bars, vals, flags):
            if val <= 0:
                continue
            ax.text(rect.get_x() + rect.get_width() / 2,
                    val + 0.02, f"{val:.2f}" + ("*" if flag else ""),
                    ha="center", va="bottom", fontsize=8)

    ax.axhline(1.0, color="#555555", linewidth=1, linestyle="--", zorder=0)
    ax.text(-0.45, 1.0, "team median = 1.00", va="bottom", ha="left",
            fontsize=8, color="#555555")
    ax.set_xticks(x)
    ax.set_xticklabels(positions_order)
    ax.set_ylabel("Mean pay index (salary / team median)")
    lvl = "Broad" if level == "broad" else "Granular"
    title = f"Position pay index — {lvl} positions"
    if season:
        title += f"  ·  {season}"
    ax.set_title(title)
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    ax.margins(y=0.15)
    fig.text(0.01, 0.005, "* mean hides high cross-club spread (CV ≥ 0.35)",
             fontsize=7, color="#777777")
    fig.tight_layout()

    out_path = out_path or (config.CHARTS / f"index_{level}.png")
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path
