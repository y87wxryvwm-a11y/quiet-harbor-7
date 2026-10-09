"""Figures for the final population: outstanding TLAC bonds of the 16 non-US,
non-China G-SIB groups. Amounts are principal outstanding in US dollars.

Put in input/: nothing new. Reads output/final_population.xlsx from 3_clean.py.

Creates (in output/):
  fig01_type.png            N and Amt Out by type
  fig02_gsib.png            N and Amt Out by G-SIB, split by type
  fig03_country.png         N and Amt Out by home country, split by type
  fig04_size.png            distribution of bond size, and cumulative share
                            of Amt Out against cumulative share of bonds
  fig05_currency.png        N and Amt Out by currency, split by type
"""

# %% Load
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from kit import load_output, save_figure

df = load_output("final_population.xlsx", require=["G-SIB", "Type", "Amt Out", "Currency group"])
df["Amt Out"] = pd.to_numeric(df["Amt Out"])
df["bn"] = df["Amt Out"] / 1e9
TYPES = ["AT1", "Tier 2", "Senior"]
COLORS = {"AT1": "#1b3a5c", "Tier 2": "#4f81b0", "Senior": "#a9c4de"}
plt.rcParams.update({
    "font.family": "serif", "font.size": 9, "axes.titlesize": 10, "axes.spines.top": False,
    "axes.spines.right": False, "legend.frameon": False, "figure.dpi": 100,
})


def stacked_barh(ax, table, xlabel):
    """Horizontal bars split by type; table rows are groups, columns types."""
    left = np.zeros(len(table))
    for t in TYPES:
        ax.barh(table.index, table[t], left=left, color=COLORS[t], label=t)
        left += table[t].values
    ax.set_xlabel(xlabel)


def by_group_figure(by, title, filename):
    n = df.pivot_table(index=by, columns="Type", values="bn", aggfunc="size", fill_value=0).reindex(columns=TYPES, fill_value=0)
    amt = df.pivot_table(index=by, columns="Type", values="bn", aggfunc="sum", fill_value=0).reindex(columns=TYPES, fill_value=0)
    order = amt.sum(axis=1).sort_values(ascending=False).index
    fig, (a, b) = plt.subplots(1, 2, figsize=(7.5, 0.28 * len(order) + 1.4), sharey=True)
    stacked_barh(a, n.loc[order], "Number of bonds")
    stacked_barh(b, amt.loc[order], "Amount outstanding (USD bn)")
    a.set_title("(a) Number of bonds")
    b.set_title("(b) Amount outstanding")
    a.invert_yaxis()
    fig.suptitle(title, fontsize=11)
    fig.tight_layout()
    fig.legend(*a.get_legend_handles_labels(), ncol=3, loc="upper center", bbox_to_anchor=(0.5, 0.01))
    save_figure(fig, filename)


# %% Figure 1: type
n = df["Type"].value_counts().reindex(TYPES)
amt = df.groupby("Type")["bn"].sum().reindex(TYPES)
fig, (a, b) = plt.subplots(1, 2, figsize=(7.5, 3))
a.bar(TYPES, n, color=[COLORS[t] for t in TYPES])
b.bar(TYPES, amt, color=[COLORS[t] for t in TYPES])
a.set_ylabel("Number of bonds")
b.set_ylabel("Amount outstanding (USD bn)")
a.set_title("(a) Number of bonds")
b.set_title("(b) Amount outstanding")
for ax, values, fmt in [(a, n, "{:,.0f}"), (b, amt, "{:,.0f}")]:
    for x, v in zip(TYPES, values):
        ax.annotate(fmt.format(v), (x, v), ha="center", va="bottom", fontsize=8)
fig.suptitle("TLAC bonds outstanding by instrument type", fontsize=11)
fig.tight_layout()
save_figure(fig, "fig01_type.png")

# %% Figures 2-3: G-SIB and home country
by_group_figure("G-SIB", "TLAC bonds outstanding by G-SIB", "fig02_gsib.png")
by_group_figure("Home country", "TLAC bonds outstanding by home country", "fig03_country.png")

# %% Figure 4: size distribution
fig, (a, b) = plt.subplots(1, 2, figsize=(7.5, 3.2))
bins = np.logspace(np.log10(df["Amt Out"].min()), np.log10(df["Amt Out"].max()), 40)
a.hist([df.loc[df["Type"] == t, "Amt Out"] for t in TYPES], bins=bins, stacked=True,
       color=[COLORS[t] for t in TYPES], label=TYPES)
a.set_xscale("log")
a.set_xticks([1e5, 1e6, 1e7, 1e8, 1e9, 1e10], ["0.1", "1", "10", "100", "1,000", "10,000"])
a.set_xlabel("Amount outstanding per bond (USD m, log scale)")
a.set_ylabel("Number of bonds")
a.set_title("(a) Distribution of bond size")
a.legend(loc="upper left")
sizes = np.sort(df["Amt Out"].values)
b.plot(np.arange(1, len(sizes) + 1) / len(sizes) * 100, sizes.cumsum() / sizes.sum() * 100, color=COLORS["AT1"])
b.plot([0, 100], [0, 100], color="grey", linewidth=0.8, linestyle="--")
b.set_xlim(0, 100)
b.set_ylim(0, 100)
b.set_xlabel("Cumulative % of bonds (smallest to largest)")
b.set_ylabel("Cumulative % of amount outstanding")
b.set_title("(b) Cumulative share of amount outstanding")
fig.suptitle("Size of TLAC bonds", fontsize=11)
fig.tight_layout()
save_figure(fig, "fig04_size.png")

# %% Figure 5: currency
by_group_figure("Currency group", "TLAC bonds outstanding by currency", "fig05_currency.png")
