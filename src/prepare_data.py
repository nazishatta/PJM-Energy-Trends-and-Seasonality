from pathlib import Path
import pandas as pd


# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

RAW_FILE = ROOT / "data" / "raw" / "PJME_hourly.csv"
PROCESSED_DIR = ROOT / "data" / "processed"

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# 1. Load raw data
# ---------------------------------------------------------

df = pd.read_csv(RAW_FILE)

print("\n=== RAW DATA ===")
print("Rows:", len(df))
print("Columns:", df.columns.tolist())


# ---------------------------------------------------------
# 2. Parse dates and numeric values
# ---------------------------------------------------------

df["Datetime"] = pd.to_datetime(
    df["Datetime"],
    errors="coerce"
)

df["PJME_MW"] = pd.to_numeric(
    df["PJME_MW"],
    errors="coerce"
)

print("\nUnparseable dates:", df["Datetime"].isna().sum())
print("Missing MW values:", df["PJME_MW"].isna().sum())


# ---------------------------------------------------------
# 3. Remove unusable rows, then SORT chronologically
# ---------------------------------------------------------

df = (
    df
    .dropna(subset=["Datetime", "PJME_MW"])
    .sort_values("Datetime")
    .reset_index(drop=True)
)

print("\n=== CHRONOLOGICAL COVERAGE ===")
print("Start:", df["Datetime"].min())
print("End:  ", df["Datetime"].max())


# ---------------------------------------------------------
# 4. Identify duplicate local timestamps
# ---------------------------------------------------------

counts = (
    df.groupby("Datetime")
      .size()
      .rename("source_count")
)

duplicate_times = counts[counts > 1]

print("\n=== DUPLICATE TIMESTAMPS ===")
print(duplicate_times)

# Because the source contains naive local timestamps without
# UTC offsets, duplicate clock times cannot safely be assigned
# separate timezone offsets.
#
# We therefore average observations sharing the same local
# timestamp while retaining source_count as a data-quality flag.

hourly = (
    df.groupby("Datetime")["PJME_MW"]
      .mean()
      .to_frame()
      .join(counts)
)


# ---------------------------------------------------------
# 5. Construct a complete regular hourly grid
# ---------------------------------------------------------

full_index = pd.date_range(
    start=hourly.index.min(),
    end=hourly.index.max(),
    freq="h"
)

hourly = hourly.reindex(full_index)
hourly.index.name = "Datetime"

hourly["was_missing"] = hourly["PJME_MW"].isna()

hourly["source_count"] = (
    hourly["source_count"]
    .fillna(0)
    .astype(int)
)

hourly["was_duplicate"] = hourly["source_count"] > 1


# ---------------------------------------------------------
# 6. Fill isolated missing hourly observations
# ---------------------------------------------------------

hourly["PJME_MW_clean"] = (
    hourly["PJME_MW"]
    .interpolate(
        method="time",
        limit=1
    )
)

hourly["was_imputed"] = hourly["was_missing"]


# ---------------------------------------------------------
# 7. Validation
# ---------------------------------------------------------

print("\n=== CLEANING SUMMARY ===")
print("Regular hourly rows:", len(hourly))
print("Duplicate timestamps resolved:", int(hourly["was_duplicate"].sum()))
print("Missing hours identified:", int(hourly["was_missing"].sum()))
print(
    "Missing values after interpolation:",
    int(hourly["PJME_MW_clean"].isna().sum())
)

print(
    "Chronologically sorted:",
    hourly.index.is_monotonic_increasing
)


# ---------------------------------------------------------
# 8. Save canonical hourly dataset
# ---------------------------------------------------------

hourly.to_csv(
    PROCESSED_DIR / "PJME_hourly_clean.csv"
)


# ---------------------------------------------------------
# 9. Produce resolution-specific datasets
#
# PJME_MW is electricity DEMAND measured in MW.
# We therefore use MEAN when changing temporal resolution.
#
# Summing MW would change the interpretation toward energy
# and should not be presented as average electricity demand.
# ---------------------------------------------------------

s = hourly["PJME_MW_clean"]

resolutions = {
    "daily": "D",
    "weekly": "W",
    "monthly": "MS",
    "quarterly": "QS",
    "yearly": "YS",
}

for name, rule in resolutions.items():

    out = (
        s.resample(rule)
         .mean()
         .rename("PJME_MW")
         .to_frame()
    )

    out.to_csv(
        PROCESSED_DIR / f"PJME_{name}.csv"
    )

    print(
        f"{name.capitalize():10s}: "
        f"{len(out):5d} rows | "
        f"{out.index.min()} -> {out.index.max()}"
    )


print("\nProcessed datasets created successfully.")
