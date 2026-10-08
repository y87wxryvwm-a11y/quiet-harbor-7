"""First summary statistics of outstanding TLAC bonds of the 16 non-US,
non-China G-SIB groups. Amounts are principal outstanding in US dollars,
as converted by Bloomberg; not market value.

Put in input/: nothing new. Reads output/clean.csv from 3_clean.py.

Creates:
  output/summary.xlsx   seven sheets, each meant to fit one screen:
                        Overview   bonds and dollars by type (AT1, Tier 2,
                                   Senior), with mean and median size
                        G-SIBs     by banking group, with concentration
                        Countries  by home country, with concentration
                        Size       how big bonds are, in size bands
                        Currency   USD, EUR, GBP, CAD, JPY, ... shares
                        Features   coupon, call structure, years left, rating
                        US market  share sold into the US market (US ISIN or
                                   144A), a stand-in for US ownership
"""

# %% Load
import pandas as pd

from kit import load_output, save_output

df = load_output("clean.csv", require=["G-SIB", "Type", "Amt Out", "US market"])
df["Amt Out"] = pd.to_numeric(df["Amt Out"])
df["Years to maturity"] = pd.to_numeric(df["Years to maturity"], errors="coerce")
df["usd"] = (df["Currency"] == "USD") * df["Amt Out"]
df["us"] = (df["US market"] == "Yes") * df["Amt Out"]
TYPES = ["AT1", "Tier 2", "Senior"]
total_bn = df["Amt Out"].sum() / 1e9


def summarize(by, order=None):
    """Bonds and dollars per group, with shares, plus a Total row."""
    t = df.groupby(by).agg(Bonds=("Amt Out", "size"), amt=("Amt Out", "sum"))
    if order:
        t = t.reindex(order).dropna(how="all")
    t.loc["Total"] = [len(df), df["Amt Out"].sum()]
    t["Share of bonds"] = (t["Bonds"] / len(df)).map("{:.1%}".format)
    t["Amt Out ($bn)"] = (t["amt"] / 1e9).round(1)
    t["Share of $"] = (t["amt"] / df["Amt Out"].sum()).map("{:.1%}".format)
    t["Bonds"] = t["Bonds"].astype(int)
    return t


def by_type(by):
    """Dollars per group split into AT1, Tier 2, Senior ($bn)."""
    t = df.pivot_table(index=by, columns="Type", values="Amt Out", aggfunc="sum", fill_value=0)
    t = t.reindex(columns=TYPES, fill_value=0)
    t.loc["Total"] = t.sum()
    return (t / 1e9).round(1).add_suffix(" ($bn)")


def hhi(by):
    """Concentration score, 0-10,000: sum of squared % shares of dollars."""
    shares = df.groupby(by)["Amt Out"].sum() / df["Amt Out"].sum() * 100
    return round((shares**2).sum())


def size_line(name, amounts):
    m = amounts / 1e6
    return (
        f"{name}: mean {m.mean():,.0f}, p10 {m.quantile(.1):,.0f}, p25 {m.quantile(.25):,.0f}, "
        f"median {m.median():,.0f}, p75 {m.quantile(.75):,.0f}, p90 {m.quantile(.9):,.0f}, max {m.max():,.0f}"
    )


# %% Overview by type
overview = summarize("Type", TYPES)
overview["Mean ($m)"] = (df.groupby("Type")["Amt Out"].mean().reindex(overview.index).fillna(df["Amt Out"].mean()) / 1e6).round(0)
overview["Median ($m)"] = (df.groupby("Type")["Amt Out"].median().reindex(overview.index).fillna(df["Amt Out"].median()) / 1e6).round(0)
overview = overview.drop(columns="amt").rename_axis("Type").reset_index()

# %% By G-SIB and by country
gsibs = summarize("G-SIB").sort_values("amt", ascending=False)
gsibs = gsibs.loc[[i for i in gsibs.index if i != "Total"] + ["Total"]]
gsibs.insert(0, "Home country", df.groupby("G-SIB")["Home country"].first())
gsibs = gsibs.join(by_type("G-SIB")).drop(columns="amt").rename_axis("G-SIB").reset_index()
top5 = df.groupby("G-SIB")["Amt Out"].sum().nlargest(5).sum() / df["Amt Out"].sum()

countries = summarize("Home country").sort_values("amt", ascending=False)
countries = countries.loc[[i for i in countries.index if i != "Total"] + ["Total"]]
countries = countries.join(by_type("Home country")).drop(columns="amt").rename_axis("Home country").reset_index()

# %% Size bands
bands = [0, 10e6, 100e6, 500e6, 1e9, 2e9, float("inf")]
labels = ["Under $10m", "$10m-100m", "$100m-500m", "$500m-1bn", "$1bn-2bn", "$2bn and up"]
df["Size band"] = pd.cut(df["Amt Out"], bands, labels=labels, right=False).astype(str)
size = summarize("Size band", labels)
size = size.join(df.pivot_table(index="Size band", columns="Type", values="Amt Out", aggfunc="size", fill_value=0)
                 .reindex(columns=TYPES, fill_value=0).add_suffix(" bonds"))
size.loc["Total", [f"{t} bonds" for t in TYPES]] = df["Type"].value_counts().reindex(TYPES, fill_value=0).values
size[[f"{t} bonds" for t in TYPES]] = size[[f"{t} bonds" for t in TYPES]].astype(int)
size = size.drop(columns="amt").rename_axis("Size band").reset_index()

# %% Currency
currency = summarize("Currency group", ["USD", "EUR", "GBP", "CAD", "JPY", "AUD", "CHF", "Other"])
for t in TYPES:
    amt = df[df["Type"] == t].groupby("Currency group")["Amt Out"].sum()
    currency[f"{t}: share of $"] = (amt.reindex(currency.index) / amt.sum()).fillna(0).map("{:.1%}".format)
    currency.loc["Total", f"{t}: share of $"] = "100.0%"
currency = currency.drop(columns="amt").rename_axis("Currency").reset_index()

# %% Features
mty = df["Mty Type"].str.upper()
df["Call structure"] = "Other"
df.loc[mty.str.contains("CALL"), "Call structure"] = "Callable"
df.loc[mty == "AT MATURITY", "Call structure"] = "Bullet (repaid at maturity)"
df.loc[mty.str.contains("PERP"), "Call structure"] = "Perpetual"
years = [0, 1, 3, 5, 10, 20, float("inf")]
year_labels = ["Under 1 year", "1-3 years", "3-5 years", "5-10 years", "10-20 years", "20+ years"]
df["Years left"] = pd.cut(df["Years to maturity"], years, labels=year_labels, right=False).astype(str)
df.loc[df["Perpetual"] == "Yes", "Years left"] = "Perpetual"
rating = df["BBG Composite"].str.replace("+", "").str.replace("-", "")
df["Rating"] = rating.where(rating.isin(["AAA", "AA", "A", "BBB", "BB", "B"]), "Not rated / none")
df["Rating"] = df["Rating"].where(df["Rating"] == "Not rated / none", df["Rating"] + " range")

features = pd.concat(
    [
        summarize(col, order).drop(index="Total").assign(Feature=col).rename_axis("Value").reset_index()
        for col, order in [
            ("Coupon Type", None),
            ("Call structure", ["Bullet (repaid at maturity)", "Callable", "Perpetual", "Other"]),
            ("Years left", year_labels + ["Perpetual"]),
            ("Rating", ["AAA range", "AA range", "A range", "BBB range", "BB range", "B range", "Not rated / none"]),
        ]
    ]
)[["Feature", "Value", "Bonds", "Share of bonds", "Amt Out ($bn)", "Share of $"]]
dated = df["Years to maturity"].dropna()
dated_amt = df.loc[dated.index, "Amt Out"]

# %% US market (stand-in for US ownership)


def us_rows(by, order=None):
    t = df.groupby(by).agg(Bonds=("Amt Out", "size"), amt=("Amt Out", "sum"),
                           us_n=("US market", lambda s: (s == "Yes").sum()), us=("us", "sum"), usd=("usd", "sum"))
    return t.reindex(order) if order else t.sort_values("amt", ascending=False)


us = pd.concat([
    pd.DataFrame({"Bonds": [len(df)], "amt": [df["Amt Out"].sum()], "us_n": [(df["US market"] == "Yes").sum()],
                  "us": [df["us"].sum()], "usd": [df["usd"].sum()]}, index=["All bonds"]),
    us_rows("Type", TYPES),
    us_rows("Home country"),
])
us["Amt Out ($bn)"] = (us["amt"] / 1e9).round(1)
us["US market: share of bonds"] = (us["us_n"] / us["Bonds"]).map("{:.1%}".format)
us["US market: share of $"] = (us["us"] / us["amt"]).map("{:.1%}".format)
us["US market ($bn)"] = (us["us"] / 1e9).round(1)
us["In USD: share of $"] = (us["usd"] / us["amt"]).map("{:.1%}".format)
us = us.drop(columns=["amt", "us_n", "us", "usd"]).rename_axis("Group").reset_index()

# %% Save
save_output(
    {
        "Overview": overview,
        "G-SIBs": gsibs,
        "Countries": countries,
        "Size": size,
        "Currency": currency,
        "Features": features,
        "US market": us,
    },
    "summary.xlsx",
    notes={
        "Overview": [
            f"Outstanding TLAC bonds, 16 G-SIB groups: {len(df):,} bonds, ${total_bn:,.1f}bn principal (USD)",
            "AT1 = junior, mostly perpetual (the contingent convertibles); Tier 2 = subordinated; Senior = senior TLAC",
        ],
        "G-SIBs": [
            "By G-SIB group",
            f"Concentration of $ (HHI, 0-10,000; above 1,500 = moderately concentrated): {hhi('G-SIB'):,}"
            f"    Top 5 groups' share of $: {top5:.1%}",
        ],
        "Countries": [
            "By home country of the G-SIB group (not the issuing subsidiary)",
            f"Concentration of $ (HHI, 0-10,000): {hhi('Home country'):,}",
        ],
        "Size": [
            "Size of each bond (Amt Out). Per bond, $m:",
            size_line("All", df["Amt Out"]),
            *[size_line(t, df.loc[df["Type"] == t, "Amt Out"]) for t in TYPES],
        ],
        "Currency": ["By currency of the bond (amounts are all in US dollars)"],
        "Features": [
            "Bond features",
            f"Dated bonds, years to maturity: median {dated.median():.1f}, "
            f"dollar-weighted mean {(dated * dated_amt).sum() / dated_amt.sum():.1f}",
        ],
        "US market": [
            "Sold into the US market (ISIN starts with US, or 144A): a stand-in, NOT US ownership",
            "Ownership needs holder data (Bloomberg HDS or SEC N-PORT fund holdings)",
        ],
    },
)
