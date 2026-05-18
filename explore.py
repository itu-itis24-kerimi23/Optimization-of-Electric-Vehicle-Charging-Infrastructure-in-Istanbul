import pandas as pd

# print('=== SOKET ===')
# df_soket = pd.read_csv('data/raw/sarj_istasyon_soket.csv')
# print('Satir sayisi:', len(df_soket))
# print('Sutunlar:', df_soket.columns.tolist())
# print(df_soket.head(2))

# print('\n=== ISPARK ===')
# df_ispark = pd.read_csv('data/raw/ispark_parking.csv')
# print('Satir sayisi:', len(df_ispark))
# print('Sutunlar:', df_ispark.columns.tolist())
# print(df_ispark.head(2))

# print('\n=== NUFUS ===')
# df_nufus = pd.read_excel('data/raw/nufus_bilgileri.xlsx')
# print('Satir sayisi:', len(df_nufus))
# print('Sutunlar:', df_nufus.columns.tolist())
# print(df_nufus.head(3))

# print('\n=== IBB EV TOPLAM HESABI ===')
# df_ibb = pd.read_csv('data/raw/ibb_ev_yillik.csv')

# ev_columns = [
#     'IST - Otomobil ve Elektrik',
#     'IST - Minibus ve Elektrik',
#     'IST - Otobus ve Elektrik',
#     'IST - Kamyonet ve Elektrik',
#     'IST - Kamyon ve Elektrik',
#     'IST - Motosiklet ve Elektrik',
# ]

# df_ibb['total_ev'] = df_ibb[ev_columns].sum(axis=1)
# print(df_ibb[['Yil', 'total_ev']])

import sys
sys.path.append('src')
# from data_processing import load_existing_stations

# print('\n=== EXISTING STATIONS TEST ===')
# df = load_existing_stations()
# print(df.head(3))
# print('Sutunlar:', df.columns.tolist())

# from data_processing import load_candidate_stations

# print('\n=== CANDIDATE STATIONS TEST ===')
# df = load_candidate_stations()
# print('Sutunlar:', df.columns.tolist())
# print(df[['candidate_id', 'longitude', 'latitude', 'max_capacity']].head(3))

# from data_processing import load_demand_zones

# print('\n=== DEMAND ZONES TEST ===')
# df = load_demand_zones()
# print(df.columns.tolist())

# import sys
# sys.path.append('src')
# from data_processing import load_existing_stations, load_candidate_stations

# print('\n=== QUALITY CHECK ===')
# load_existing_stations()
# load_candidate_stations()

import sys
sys.path.append('src')
from distance_calculator import compute_distance_matrix

df = compute_distance_matrix()

# # D_MAX uygulanmadan önce gerçek mesafelere bak
# print('\n=== DST/0 (Adalar) en yakın 5 nokta ===')
# row = df.loc['DST/0']
# print(row[row > 0].sort_values().head(5))

# print('\n=== DST/1 (Arnavutkoy) en yakın 5 nokta ===')
# row = df.loc['DST/1']
# print(row[row > 0].sort_values().head(5))

# print('\n=== Her ilçe için erişilebilir nokta sayısı ===')
# print((df > 0).sum(axis=1).sort_values())

import pandas as pd
zones = pd.read_csv('data/processed/demand_zones.csv')
df = pd.read_csv('data/processed/distance_matrix.csv', index_col='district_id')

for dst in ['DST/14', 'DST/30', 'DST/31']:
    name = zones[zones['district_id'] == dst]['name'].values[0]
    accessible = (df.loc[dst] > 0).sum()
    print(f"{name}: {accessible} nokta erişilebilir")