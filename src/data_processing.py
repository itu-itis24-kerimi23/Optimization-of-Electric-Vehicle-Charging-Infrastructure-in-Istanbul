import pandas as pd
import geopandas as gpd
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_RAW_DIR, DATA_PROC_DIR, K_MAX_EXISTING


def load_existing_stations():
    """
    Merges charging station locations with socket data to estimate
    current capacity (Ki) for each existing station.

    Returns a DataFrame with columns:
    station_id, name, longitude, latitude, capacity
    """
    # load station locations
    stations = gpd.read_file(os.path.join(DATA_RAW_DIR, 'sarj_istasyonlari.geojson'))
    stations = stations[['ISTASYON_NO', 'AD', 'LONGITUDE', 'LATITUDE']].copy()
    stations.columns = ['station_id', 'name', 'longitude', 'latitude']

    # load socket data
    sockets = pd.read_csv(os.path.join(DATA_RAW_DIR, 'sarj_istasyon_soket.csv'))

    # Count sockets per station, this is our capacity proxy (Ki)
    capacity = sockets.groupby('ISTASYON_NO')['SOKET_NO'].count().reset_index().rename(columns={'ISTASYON_NO': 'station_id', 'SOKET_NO': 'capacity'})

    # merge stations with capacity
    existing = pd.merge(stations,capacity,on = 'station_id',)

    # Drop stations with no socket data
    existing = existing.dropna().reset_index(drop=True)

    # Cap capacity at K_MAX_EXISTING
    existing['capacity'] = existing['capacity'].clip(upper=K_MAX_EXISTING)

    # Add max_capacity column (for expansion limit)
    existing['max_capacity'] = K_MAX_EXISTING

    print(f"Existing stations loaded: {len(existing)}")
    print(existing[['station_id', 'capacity']].describe())

    return existing

def load_candidate_stations():
    """
    Loads ISPARK parking lots as candidate locations for new stations.

    Returns a DataFrame with columns:
    candidate_id, name, longitude, latitude, max_capacity, county
    """
    from config import K_MAX_CANDIDATE

    # load ISPARK data
    ispark = pd.read_csv(os.path.join(DATA_RAW_DIR, 'ispark_parking.csv'))

    # Select and rename relevant columns
    candidates = ispark[['PARK_NAME','LONGITUDE','LATITUDE','CAPACITY_OF_PARK','COUNTY_NAME']].copy()
    candidates = candidates.rename(columns={'PARK_NAME':'name','LONGITUDE':'longitude','LATITUDE':'latitude','CAPACITY_OF_PARK':'parking_capacity','COUNTY_NAME':'county'})

    # Create a candidate_id column
    candidates = candidates.reset_index(drop=True)
    candidates['candidate_id'] = 'CND/' + candidates.index.astype(str)

    # Drop rows with missing coordinates
    candidates = candidates.dropna(subset=['longitude', 'latitude'])

    # Add max_capacity column
    candidates['max_capacity'] = (candidates['parking_capacity'] / 10).clip(lower=1, upper=K_MAX_CANDIDATE).astype(int)

    print(f"Candidate stations loaded: {len(candidates)}")
    print(candidates.head(3))

    return candidates

def load_demand_zones():
    """
    Loads district-level population data and computes demand weights (wd).
    District centroids are hardcoded for reliability.

    Returns a DataFrame with columns:
    district_id, name, longitude, latitude, population, demand_weight
    """

    # District centroids (hardcoded for Istanbul's 39 districts)
    district_coords = {
        'Adalar': (29.0960, 40.8780),
        'Arnavutköy': (28.7397, 41.1833),
        'Ataşehir': (29.1307, 40.9833),
        'Avcılar': (28.7217, 40.9793),
        'Bağcılar': (28.8559, 41.0393),
        'Bahçelievler': (28.8637, 41.0003),
        'Bakırköy': (28.8731, 40.9820),
        'Başakşehir': (28.8025, 41.0923),
        'Bayrampaşa': (28.9144, 41.0443),
        'Beşiktaş': (29.0092, 41.0422),
        'Beykoz': (29.1083, 41.1333),
        'Beylikdüzü': (28.6411, 41.0003),
        'Beyoğlu': (28.9744, 41.0363),
        'Büyükçekmece': (28.5756, 41.0213),
        'Çatalca': (28.4611, 41.1433),
        'Çekmeköy': (29.1783, 41.0333),
        'Esenler': (28.8761, 41.0443),
        'Esenyurt': (28.6731, 41.0333),
        'Eyüpsultan': (28.9328, 41.0833),
        'Fatih': (28.9497, 41.0193),
        'Gaziosmanpaşa': (28.9128, 41.0643),
        'Güngören': (28.8731, 41.0213),
        'Kadıköy': (29.0833, 40.9833),
        'Kağıthane': (28.9731, 41.0783),
        'Kartal': (29.1833, 40.9003),
        'Küçükçekmece': (28.7761, 41.0003),
        'Maltepe': (29.1333, 40.9333),
        'Pendik': (29.2333, 40.8833),
        'Sancaktepe': (29.2333, 41.0003),
        'Sarıyer': (29.0333, 41.1667),
        'Silivri': (28.2467, 41.0733),
        'Sultanbeyli': (29.2667, 40.9667),
        'Sultangazi': (28.8667, 41.1000),
        'Şile': (29.6167, 41.1833),
        'Şişli': (28.9833, 41.0667),
        'Tuzla': (29.3000, 40.8167),
        'Ümraniye': (29.1167, 41.0167),
        'Üsküdar': (29.0167, 41.0333),
        'Zeytinburnu': (28.9000, 41.0000),
    }

    # Load population data
    pop = pd.read_excel(os.path.join(DATA_RAW_DIR, 'nufus_bilgileri.xlsx'))

    # Get the most recent year only
    latest_year = pop['Yıl'].max()
    pop = pop[pop['Yıl']==latest_year].copy()

    # Calculate total population per district
    age_cols = [c for c in pop.columns if 'Erkek' in c or 'Kadın' in c]
    pop['population'] = pop[age_cols].sum(axis=1)

    # Keep only district name and population
    pop = pop[['İlçe','population']].copy().rename(columns={'İlçe':'name'})
    

    # Add coordinates from district_coords dict
    pop['longitude'] = pop['name'].map(lambda x: district_coords.get(x, (None, None))[0])
    pop['latitude'] = pop['name'].map(lambda x: district_coords.get(x, (None, None))[1])

    # Drop districts not in our coords dict
    pop = pop.dropna(subset=['longitude', 'latitude']).reset_index(drop=True)

    # Calculate demand weight (wd)
    pop['demand_weight'] = pop['population'] / pop['population'].sum()

    # Add district_id column
    pop['district_id'] = 'DST/' + pop.index.astype(str)

    print(f"Demand zones loaded: {len(pop)}")
    print(f"Total population: {pop['population'].sum():,}")
    print(f"Demand weights sum: {pop['demand_weight'].sum():.4f}")  # it must be close to the 1.0
    print(pop.head(3))

    return pop

def save_processed_data(existing, candidates, demand_zones):
    """
    Saves processed DataFrames to data/processed/ directory.
    """
    os.makedirs(DATA_PROC_DIR, exist_ok=True)

    existing.to_csv(os.path.join(DATA_PROC_DIR,'existing_stations.csv'),index = False)
    candidates.to_csv(os.path.join(DATA_PROC_DIR,'candidate_stations.csv'),index = False)
    demand_zones.to_csv(os.path.join(DATA_PROC_DIR,'demand_zones.csv'),index = False)


    print("All processed data saved to data/processed/")


def run_pipeline():
    """
    Runs the full data processing pipeline.
    Loads, processes, and saves all datasets.
    """
    print("=== Running Data Processing Pipeline ===\n")

    existing = load_existing_stations()
    candidates = load_candidate_stations()
    demand_zones = load_demand_zones()
    save_processed_data(existing,candidates,demand_zones)

    print("\n=== Pipeline Complete ===")
    return existing, candidates, demand_zones