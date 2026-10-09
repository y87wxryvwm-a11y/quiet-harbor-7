"""Summary statistics of the final population: outstanding TLAC bonds of the
16 non-US, non-China G-SIB groups. Amounts are principal outstanding in US
dollars, as converted by Bloomberg; not market value. N = number of bonds.

Put in input/: nothing new. Reads output/final_population.xlsx from 3_clean.py.

Creates:
  output/summary.xlsx   one table per sheet:
                        Descriptive    N, mean, SD and percentiles of size,
                                       coupon and years to maturity, by type
                        Type           AT1, Tier 2, Senior
                        G-SIB          by banking group, split by type, with
                                       AT1's share; largest Amt Out first
                        Country        the same by home country
                        Currency       the same by currency
"""

# %% Load
import pandas as pd

from kit import load_output, save_output

df = load_output("final_population.xlsx", require=["G-SIB", "Type", "Amt Out"])
for col in ["Amt Out", "Coupon", "Years to maturity"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")
TYPES = ["AT1", "Tier 2", "Senior"]
N, AMT = len(df), df["Amt Out"].sum()


def counts(by, order=None):
    """N, Amt Out and shares per group, with a Total row."""
    t = df.groupby(by).agg(**{"N": ("Amt Out", "size"), "amt": ("Amt Out", "sum")})
    t = t.reindex(order).dropna(how="all") if order else t.sort_values("amt", ascending=False)
    t.loc["Total"] = [N, AMT]
    t["N"] = t["N"].astype(int)
    t["% of N"] = (100 * t["N"] / N).round(1)
    t["Amt Out (USD bn)"] = (t["amt"] / 1e9).round(1)
    t["% of Amt Out"] = (100 * t["amt"] / AMT).round(1)
    return t.drop(columns="amt")


def by_type(by):
    """Amt Out per group split into AT1, Tier 2, Senior (USD bn)."""
    t = df.pivot_table(index=by, columns="Type", values="Amt Out", aggfunc="sum", fill_value=0)
    t = t.reindex(columns=TYPES, fill_value=0)
    t.loc["Total"] = t.sum()
    return (t / 1e9).round(1).add_suffix(" (USD bn)")


# %% Descriptive statistics
rows = []
for name, col, scale in [("Amt Out (USD m)", "Amt Out", 1e6), ("Coupon (%)", "Coupon", 1),
                         ("Years to maturity", "Years to maturity", 1)]:
    for t in ["All"] + TYPES:
        x = (df[col] if t == "All" else df.loc[df["Type"] == t, col]).dropna() / scale
        if x.empty:
            continue
        rows.append({"Variable": name, "Type": t, "N": len(x), "Mean": x.mean(), "SD": x.std(),
                     "Min": x.min(), "P25": x.quantile(.25), "Median": x.median(),
                     "P75": x.quantile(.75), "Max": x.max()})
descriptive = pd.DataFrame(rows).round(2)

# %% Type
types = counts("Type", TYPES)
types["Mean (USD m)"] = (df.groupby("Type")["Amt Out"].mean().reindex(types.index).fillna(df["Amt Out"].mean()) / 1e6).round(0)
types["Median (USD m)"] = (df.groupby("Type")["Amt Out"].median().reindex(types.index).fillna(df["Amt Out"].median()) / 1e6).round(0)
types = types.rename_axis("Type").reset_index()



# %% G-SIB, country, currency: the same table for three groupings
def breakdown(by):
    """N and Amt Out per group, split by type, with AT1's share; largest Amt Out first."""
    t = counts(by).join(by_type(by))
    t.insert(t.columns.get_loc("AT1 (USD bn)") + 1, "AT1 (% of Amt Out)",
             (100 * t["AT1 (USD bn)"] / t["Amt Out (USD bn)"]).round(1))
    return t.rename_axis(by).reset_index()


gsib = breakdown("G-SIB")
gsib.insert(1, "Home country", gsib["G-SIB"].map(df.groupby("G-SIB")["Home country"].first()))
country = breakdown("Home country")
currency = breakdown("Currency group").rename(columns={"Currency group": "Currency"})


# %% Save
save_output(
    {
        "Descriptive": descriptive,
        "Type": types,
        "G-SIB": gsib,
        "Country": country,
        "Currency": currency,
    },
    "summary.xlsx",
)
