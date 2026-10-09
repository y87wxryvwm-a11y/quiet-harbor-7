"""Turn the combined Bloomberg list into the final population: one row per
outstanding TLAC bond of the 16 non-US, non-China G-SIB groups. Amounts are
in US dollars (Bloomberg was set to USD).

Population levels, each one the previous level minus one exclusion:
  1. Raw: every line in the Bloomberg export (SRCH of active bonds with
     TLAC / MREL Desig = TLAC, G-SIB = Y, country of domicile not US or
     China).
  2. Ultimate parent is one of the 16 G-SIB groups (drops US and Chinese
     parents that came in through subsidiaries abroad).
  3. Amount outstanding above zero.
  4. Not matured: maturity after today, or perpetual.
  5. No repeat lines: drops lines with no ISIN that repeat a line with an
     ISIN (same parent, coupon, maturity, currency and amount).
  6. Final: each 144A / Reg S pair counted once. The same deal is often
     listed twice, once for US buyers (144A) and once for buyers abroad
     (Reg S), and both lines carry the full amount. Lines with the same
     parent, coupon, maturity, currency and amount are merged when one is
     144A or Reg S, or when one has a US ISIN and another doesn't.

Added columns (final population):
  G-SIB             short group name
  Home country      the group's home country (not the issuing subsidiary's)
  Type              AT1 (junior, incl. CoCos), Tier 2 (subordinated), Senior
  Perpetual         Yes if the bond has no maturity date
  Years to maturity from today; blank for perpetuals
  US market         Yes if sold into the US market: Series is 144A, or the
                    ISIN is US + a digit (a US CUSIP) and Series isn't Reg S.
                    US + a letter is a foreign-style code often used for
                    Reg S lines, so it alone doesn't count. A merged pair is
                    Yes if any of its lines is.
  Series clean      Series in capitals, #N/A as blank
  Currency group    USD, EUR, GBP, CAD, JPY, AUD, CHF or Other
  Lines merged      how many Bloomberg lines this row stands for (usually 1)
  Reg S line ISIN (dropped at Level 6)
                    for a 144A / Reg S pair, the ISIN of the other line,
                    which is listed on the Level 6 sheet; blank otherwise
  Size band         Amt Out in bands: under $10m, $10m-100m, ... $2bn and up
  Years left        years to maturity in bands, or Perpetual
  Call structure    Callable, Bullet (repaid at maturity), Perpetual, Other
  Rating group      BBG Composite without +/-: AAA ... B, or Not rated

Put in input/: nothing new. Reads output/combined.csv from 1_combine.py.

Creates:
  output/final_population.xlsx
                            the final population, one row per bond, with the
                            added columns (read by the next steps)
  output/population.xlsx    Population: each level, its size, and what was
                            excluded to get there
                            Level 2 ... Level 6: the rows dropped at each
                            level (no row appears twice)
                            Final population: the rows left after level 6
"""

# %% Load
from datetime import date

import pandas as pd

from kit import load_output, save_output

raw = load_output("combined.csv", require=["Ultimate Parent", "Amt Out", "Maturity", "ISIN", "Series"])
df = raw.copy()

# Ultimate Parent starts with -> (short name, home country).
# Bloomberg cuts parent names at 30 characters, so match on the start.
GSIBS = {
    "Royal Bank of Canada": ("RBC", "Canada"),
    "Toronto-Dominion": ("TD", "Canada"),
    "BNP Paribas": ("BNP Paribas", "France"),
    "Credit Agricole": ("Credit Agricole", "France"),
    "Societe Generale": ("Societe Generale", "France"),
    "Groupe BPCE": ("BPCE", "France"),
    "Deutsche Bank": ("Deutsche Bank", "Germany"),
    "Mitsubishi UFJ": ("MUFG", "Japan"),
    "Mizuho": ("Mizuho", "Japan"),
    "Sumitomo Mitsui": ("SMFG", "Japan"),
    "ING Groep": ("ING", "Netherlands"),
    "Banco Santander": ("Santander", "Spain"),
    "UBS Group": ("UBS", "Switzerland"),
    "Barclays": ("Barclays", "United Kingdom"),
    "HSBC": ("HSBC", "United Kingdom"),
    "Standard Chartered": ("Standard Chartered", "United Kingdom"),
}
NA = "#N/A Field Not Applicable"
TODAY = pd.Timestamp(date.today())

df["Amt Out"] = pd.to_numeric(df["Amt Out"].str.replace(",", ""), errors="coerce")
df["Coupon"] = pd.to_numeric(df["Coupon"], errors="coerce")
df["Maturity"] = pd.to_datetime(df["Maturity"].replace(NA, ""), errors="coerce", format="mixed")
levels = [("Level 1 - raw", "Active bonds in Bloomberg, marked as TLAC, issued by G-SIB companies based "
                    "outside the US and China, that...", "", df.index)]


def step(sheet, population, excluded, keep):
    """Apply one cleaning step and record the level it leaves."""
    global df
    df = df[keep].copy()
    levels.append((sheet, population, excluded, df.index))


# %% 2. The 16 G-SIB groups
match = df["Ultimate Parent"].map(lambda p: next((v for k, v in GSIBS.items() if p.startswith(k)), None))
df["G-SIB"] = match.str[0]
df["Home country"] = match.str[1]
step("Level 2 - US or CN parents", "...belong to a banking group whose parent is not American or Chinese, that...",
     "US or Chinese ultimate parent", match.notna())

# %% 3-4. Outstanding today
step("Level 3 - nothing outstanding", "...still have money owed to investors, that...", "Amount outstanding zero or blank", df["Amt Out"] > 0)
step("Level 4 - matured", "...have not reached their repayment date, or have none, that...", "Matured", ~(df["Maturity"] < TODAY))

# %% 5. Lines without an ISIN that repeat a bond
terms = ["Ultimate Parent", "Coupon", "Maturity", "Currency", "Amt Out"]


def same_terms():
    """Group lines with the same parent, coupon, maturity, currency, amount."""
    return df.fillna({"Maturity": pd.Timestamp("2200-01-01")}).groupby(terms, dropna=False)


has_isin = df["ISIN"].str.len() == 12
repeats = same_terms()["ISIN"].transform(lambda s: (s.str.len() == 12).any())
step("Level 5 - repeat lines", "...are not a second listing of a bond already counted, and that...",
     "No ISIN; same parent, coupon, maturity, currency and amount as a line with an ISIN",
     has_isin | ~repeats)

# %% 6. 144A / Reg S pairs
df["Series clean"] = df["Series"].str.upper().str.replace(" ", "").replace({NA.upper().replace(" ", ""): ""})
df["US ISIN"] = df["ISIN"].str.startswith("US")
group = same_terms()
df["Lines merged"] = group["ISIN"].transform("size")
pair = (
    group["Series clean"].transform(lambda s: s.isin(["144A", "REGS"]).any())
    | (group["US ISIN"].transform("any") & ~group["US ISIN"].transform("all"))
)
df["US market"] = (df["Series clean"] == "144A") | (
    df["ISIN"].str.match(r"US\d") & (df["Series clean"] != "REGS")
)
df["US line"] = df["US market"]
df["US market"] = df["US market"] | (pair & same_terms()["US market"].transform("any"))
df["Twin"] = (df["Lines merged"] > 1) & pair
df["Group id"] = group.ngroup()
group_isins = df[df["Twin"]].groupby("Group id")["ISIN"].agg(list)
# Keep one line per pair, preferring the US one; other lines stand for themselves.
df = df.assign(not_regs=df["Series clean"] != "REGS").sort_values(
    ["US line", "not_regs"], ascending=False, kind="stable").drop(columns="not_regs")
step("Level 6 - 144A-Reg S pairs", "...are counted once when the same deal is listed separately for US and non-US buyers.",
     "Second line of a 144A / Reg S pair", ~(df["Twin"] & df.duplicated("Group id")))
df.loc[~df["Twin"], "Lines merged"] = 1
df["Reg S line ISIN (dropped at Level 6)"] = [
    ", ".join(i for i in group_isins[g] if i != own) if twin else ""
    for g, own, twin in zip(df["Group id"], df["ISIN"], df["Twin"])
]

# %% Added columns
perpetual = df["Maturity"].isna()
df["Type"] = "Senior"
df.loc[df["MiFID Bond Seniority"] == "SBOD", "Type"] = "Tier 2"
df.loc[(df["MiFID Bond Seniority"] == "JUND") | perpetual, "Type"] = "AT1"
df["Perpetual"] = perpetual.map({True: "Yes", False: "No"})
df["Years to maturity"] = ((df["Maturity"] - TODAY).dt.days / 365.25).round(2)
df["US market"] = df["US market"].map({True: "Yes", False: "No"})
main = ["USD", "EUR", "GBP", "CAD", "JPY", "AUD", "CHF"]
df["Currency group"] = df["Currency"].where(df["Currency"].isin(main), "Other")
df["Maturity"] = df["Maturity"].dt.strftime("%Y-%m-%d")
SIZE_BANDS = ["Under $10m", "$10m-100m", "$100m-500m", "$500m-1bn", "$1bn-2bn", "$2bn and up"]
df["Size band"] = pd.cut(df["Amt Out"], [0, 10e6, 100e6, 500e6, 1e9, 2e9, float("inf")],
                         labels=SIZE_BANDS, right=False).astype(str)
YEAR_BANDS = ["Under 1 year", "1-3 years", "3-5 years", "5-10 years", "10-20 years", "20+ years"]
df["Years left"] = pd.cut(df["Years to maturity"], [0, 1, 3, 5, 10, 20, float("inf")],
                          labels=YEAR_BANDS, right=False).astype(str)
df.loc[perpetual, "Years left"] = "Perpetual"
mty = df["Mty Type"].str.upper()
df["Call structure"] = "Other"
df.loc[mty.str.contains("CALL"), "Call structure"] = "Callable"
df.loc[mty == "AT MATURITY", "Call structure"] = "Bullet (repaid at maturity)"
df.loc[mty.str.contains("PERP"), "Call structure"] = "Perpetual"
rating = df["BBG Composite"].str.replace("+", "").str.replace("-", "")
df["Rating group"] = rating.where(rating.isin(["AAA", "AA", "A", "BBB", "BB", "B"]), "Not rated")
df = df.drop(columns=["US ISIN", "US line", "Twin", "Group id"]).sort_values(["G-SIB", "Maturity"])

# %% Column order: identifiers, then what the analysis uses, then the rest
FIRST = [
    "G-SIB", "Ultimate Parent", "Issuer Name", "Sec Short Desc", "ISIN", "Reg S line ISIN (dropped at Level 6)",
    "Series", "Home country", "Type", "Amt Out", "Currency", "Currency group", "Size band", "Maturity",
    "Years to maturity", "Years left", "Perpetual", "Call structure", "Coupon", "Coupon Type", "Rating group",
    "US market", "Lines merged", "MiFID Bond Seniority", "Mty Type", "BBG Composite", "Series clean",
]
df = df[FIRST + [c for c in df.columns if c not in FIRST + ["source_file"]]]

# %% Population levels
amount = pd.to_numeric(raw["Amt Out"].str.replace(",", ""), errors="coerce").fillna(0)
raw_n, raw_amt = len(raw), amount.sum()
rows = []
for i, (sheet, text, why, idx) in enumerate(levels):
    dropped = levels[i - 1][3].difference(idx) if i else idx[:0]
    rows.append({
        "Level": sheet,
        "Population": text,
        "N": len(idx),
        "% of raw N": round(100 * len(idx) / raw_n, 1),
        "Amt Out (USD bn)": round(amount[idx].sum() / 1e9, 1),
        "% of raw Amt Out": round(100 * amount[idx].sum() / raw_amt, 1),
        "Excluded": why,
        "Excluded N": len(dropped) if i else None,
        "Excluded % of raw N": round(100 * len(dropped) / raw_n, 1) if i else None,
        "Excluded Amt Out (USD bn)": round(amount[dropped].sum() / 1e9, 1) if i else None,
        "Excluded % of raw Amt Out": round(100 * amount[dropped].sum() / raw_amt, 1) if i else None,
    })
population = pd.DataFrame(rows)
population["Excluded N"] = population["Excluded N"].astype("Int64")

shown = raw.drop(columns="source_file")
for col in ["Amt Out", "Amt Issued", "Coupon"]:
    numbers = pd.to_numeric(shown[col].str.replace(",", ""), errors="coerce")
    shown[col] = numbers.where(numbers.notna(), shown[col])
sheets = {"Population": population}
for i, (sheet, _, _, idx) in enumerate(levels):
    if i:
        sheets[sheet] = shown.loc[levels[i - 1][3].difference(idx)]
sheets["Final population"] = shown.loc[df.index]

# %% Save
save_output(df, "final_population.xlsx")
save_output(sheets, "population.xlsx")
