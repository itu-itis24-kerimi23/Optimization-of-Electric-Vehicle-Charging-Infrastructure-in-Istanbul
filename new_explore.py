import pandas as pd
from pathlib import Path

DATA_PROCESSED = Path("data/processed")

print("\n=== PROCESSED FILE CHECK ===")

required_files = {
    "demand": DATA_PROCESSED / "demand_zones.csv",
    "existing": DATA_PROCESSED / "existing_stations.csv",
    "candidate": DATA_PROCESSED / "candidate_stations.csv",
}

for name, path in required_files.items():
    print(f"{name}: {path} -> exists: {path.exists()}")

if not all(path.exists() for path in required_files.values()):
    raise FileNotFoundError("Some processed files are missing. Run the pipeline first.")

demand = pd.read_csv(required_files["demand"])
existing = pd.read_csv(required_files["existing"])
candidate = pd.read_csv(required_files["candidate"])


def basic_check(df, name):
    print(f"\n=== {name.upper()} ===")
    print("Rows:", len(df))
    print("Columns:", df.columns.tolist())
    print(df.head(3))

    if "latitude" in df.columns and "longitude" in df.columns:
        print("Latitude range:", df["latitude"].min(), "-", df["latitude"].max())
        print("Longitude range:", df["longitude"].min(), "-", df["longitude"].max())

    print("\nMissing values:")
    print(df.isna().sum())


basic_check(demand, "demand zones")
basic_check(existing, "existing stations")
basic_check(candidate, "candidate stations")


print("\n=== DEMAND WEIGHT CHECK ===")
if "demand_weight" in demand.columns:
    print("Demand weight sum:", demand["demand_weight"].sum())
else:
    print("demand_weight column not found")


print("\n=== CAPACITY CHECK ===")
if "capacity" in existing.columns:
    print("Existing capacity min:", existing["capacity"].min())
    print("Existing capacity max:", existing["capacity"].max())
    print("Existing capacity mean:", existing["capacity"].mean())
else:
    print("capacity column not found in existing stations")

if "max_capacity" in candidate.columns:
    print("Candidate max_capacity min:", candidate["max_capacity"].min())
    print("Candidate max_capacity max:", candidate["max_capacity"].max())
    print("Candidate max_capacity mean:", candidate["max_capacity"].mean())
else:
    print("max_capacity column not found in candidate stations")


print("\n=== DUPLICATE CHECK ===")

if "district_id" in demand.columns:
    print("Duplicate district_id:", demand["district_id"].duplicated().sum())

if "station_id" in existing.columns:
    print("Duplicate station_id:", existing["station_id"].duplicated().sum())
else:
    print("station_id column not found in existing stations")

if "candidate_id" in candidate.columns:
    print("Duplicate candidate_id:", candidate["candidate_id"].duplicated().sum())


print("\n=== COORDINATE VALIDITY CHECK ===")

def coordinate_check(df, name):
    if "latitude" not in df.columns or "longitude" not in df.columns:
        print(f"{name}: latitude/longitude columns missing")
        return

    bad_rows = df[
        (df["latitude"] < 40) |
        (df["latitude"] > 42) |
        (df["longitude"] < 27) |
        (df["longitude"] > 31)
    ]

    swapped_rows = df[
        (df["latitude"] > 27) &
        (df["latitude"] < 31) &
        (df["longitude"] > 40) &
        (df["longitude"] < 42)
    ]

    print(f"{name} bad coordinate rows:", len(bad_rows))
    print(f"{name} possible swapped coordinate rows:", len(swapped_rows))



coordinate_check(demand, "Demand zones")
coordinate_check(existing, "Existing stations")
coordinate_check(candidate, "Candidate stations")

print("\n=== BAD CANDIDATE COORDINATES ===")
bad_candidate = candidate[
    (candidate["latitude"] < 40) |
    (candidate["latitude"] > 42) |
    (candidate["longitude"] < 27) |
    (candidate["longitude"] > 31)
]

print(bad_candidate)


print("\nValidation finished.")