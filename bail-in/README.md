# Bail-in (TLAC) bonds of non-US, non-China G-SIBs

The question is how much bail-in debt (TLAC) the non-US, non-China G-SIBs have outstanding, what it looks like, and how much of it US investors hold.

The starting population comes from a Bloomberg search of active bonds, filtered in this order:

1. TLAC / MREL Designation is TLAC. 
2. G-SIB indicator is Y. 
3. Country of domicile is not the US or China. 

It was exported on October 1, 2026 in two files, one for Canada and one for all other countries. The two files are stacked into one list.

## Population

The file population.xlsx starts with a summary of each filter from the raw starting population to the final cleaned population. Each of the following sheets lists the rows dropped at each filter, and the last sheet is the final population. Together they add up to the raw starting population.

- **Level 1 - raw:** the starting population described above.
- **Level 2 - US or CN parents:** drops bonds whose ultimate parent is a US or Chinese group. These get through the Bloomberg search because the domicile filter applies to the issuing company, not the ultimate parent, and US and Chinese parents issue through subsidiaries based in other countries. 
- **Level 3 - nothing outstanding:** drops bonds with an amount outstanding of zero or blank. The question is about debt outstanding today, and these would add to the count of bonds without adding any dollars.
- **Level 4 - matured:** drops bonds whose maturity date has passed. They have been repaid, so they are no longer outstanding. Perpetual bonds are kept.
- **Level 5 - repeat lines:** drops lines without an ISIN that repeat a line with one. They have the same parent, coupon, maturity, currency and amount, so they are the same bond listed twice. Keeping them would count the bond and its dollars twice.
- **Level 6 - 144A-Reg S pairs:** many deals are listed twice, once for US buyers (144A) and once for buyers outside the US (Reg S), and both lines carry the full amount. Counting both would overstate the totals, so each deal is counted once. The line kept is the one sold to US buyers.

## Summary

Each bond is given one of three types, from riskiest to safest:

- **AT1:** first to take losses. These include the contingent convertible bonds, which turn into shares or are written down if the bank's capital falls too low. A bond is AT1 if Bloomberg ranks it as junior or it has no maturity date.
- **Tier 2:** takes losses after AT1. A bond is Tier 2 if Bloomberg ranks it as subordinated.
- **Senior:** takes losses last. All other bonds.

The sheets:

- **Descriptive:** Descriptive statistics for the the size, interest rate and years to maturity of the bonds, for all bonds and for each type. 
- **Type:** Aggregate statistics for the number of bonds and the amount outstanding for each type. 
- **G-SIB:** the same for each bank, with breakdowns by type. 
- **Country:** the same as previous sheet but by each bank's home country.
- **Currency:** the same as previous sheet but by the currency each bond was issued in.

## Figures

The figures folder shows the summary as charts.

- **fig01_type:** number of bonds and amount outstanding for each type.
- **fig02_gsib:** the same for each bank, with each bar split by type.
- **fig03_country:** the same for each bank's home country.
- **fig04_size:** on the left, how many bonds there are of each size. On the right, the bonds lined up from smallest to largest, showing what share of the total amount outstanding they add up to. The dashed line is what it would look like if all bonds were the same size.
- **fig05_currency:** the same as fig02 and fig03, for the currency each bond was issued in.
