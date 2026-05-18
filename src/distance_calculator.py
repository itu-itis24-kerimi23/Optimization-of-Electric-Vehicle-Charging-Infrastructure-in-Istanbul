import pandas as pd
import numpy as np
from haversine import haversine, Unit
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_PROC_DIR, D_MAX


def compute_distance_matrix():
    """
    Computes Haversine distance (in meters) between every demand zone
    centroid and every service point (existing + candidate stations).

    Returns a DataFrame where:
    - rows    = demand zones (district_id)
    - columns = service points (station_id or candidate_id)
    - values  = distance in meters

    Also saves the matrix to data/processed/distance_matrix.csv
    """

    # 1: Load processed data
    zones      = pd.read_csv(os.path.join(DATA_PROC_DIR, 'demand_zones.csv'))
    existing   = pd.read_csv(os.path.join(DATA_PROC_DIR, 'existing_stations.csv'))
    candidates = pd.read_csv(os.path.join(DATA_PROC_DIR, 'candidate_stations.csv'))

    # 2: Build service point list (existing + candidate)
    # Combine into one DataFrame with unified columns: point_id, latitude, longitude
    existing_points = existing[['station_id','latitude','longitude']].rename(
        columns={'station_id': 'point_id'}
    )
    candidate_points = candidates[['candidate_id','latitude','longitude']].rename(
        columns={'candidate_id': 'point_id'}
    )
    all_points = pd.concat([existing_points, candidate_points], ignore_index=True)

    print(f"Demand zones   : {len(zones)}")
    print(f"Existing       : {len(existing_points)}")
    print(f"Candidates     : {len(candidate_points)}")
    print(f"Total points   : {len(all_points)}")
    print(f"Matrix size    : {len(zones)} x {len(all_points)} = {len(zones)*len(all_points):,} cells")
    print("Computing distances...")

    # 3: Compute distance matrix
    matrix = {}
    for _, zone in zones.iterrows():
        zone_coords = (zone['latitude'], zone['longitude'])
        matrix[zone['district_id']] = {}
        for _, point in all_points.iterrows():
            point_coords = (point['latitude'], point['longitude'])
            distance = haversine(zone_coords, point_coords, unit=Unit.METERS)
            matrix[zone['district_id']][point['point_id']] = distance

    # 4: Convert to DataFrame
    distance_df = pd.DataFrame(matrix).T
    distance_df.index.name = 'district_id'

    # 5: Apply D_MAX filter
    
    distance_df = distance_df.where(distance_df <= D_MAX, other=0)

    # 6: Save to CSV
    output_path = os.path.join(DATA_PROC_DIR, 'distance_matrix.csv')
    distance_df.to_csv(output_path)
    print(f"Distance matrix saved: {distance_df.shape}")
    print(f"Points within D_MAX  : {(distance_df > 0).sum().sum():,} / {distance_df.size:,}")

    return distance_df


if __name__ == '__main__':
    print("=== Distance Calculator ===\n")
    df = compute_distance_matrix()
    print("\nSample distances (first 3 zones, first 5 points):")
    print(df.iloc[:3, :5])