import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (DATA_RAW_DIR, DATA_PROC_DIR, BASE_YEAR,
                    N_BASE, RHO, THETA_DEFAULT,
                    TURKEY_K_MIN, TURKEY_K_MAX,
                    ISTANBUL_K_MIN, ISTANBUL_K_MAX)


def logistic(t, K, r, t0):
    """
    Standard logistic growth curve.
    K  : carrying capacity (upper limit)
    r  : growth rate
    t0 : inflection point (year of fastest growth)
    """
    return K / (1 + np.exp(-r * (t - t0)))


def load_turkey_ev_series():
    """
    Builds the Turkey-wide EV time series used to validate the growth pattern.

    Combines two sources:
      1. Historical points (2015-2019) from external references stored in
         turkey_ev_historical.csv
      2. Recent points (2020-2024) computed from the IBB raw dataset by
         summing Turkey-wide electric vehicle counts excluding motorcycles
         (since e-motorcycles mostly do not use public car chargers)

    Returns a DataFrame with columns: year, total_ev
    """
    historical = pd.read_csv(os.path.join(DATA_RAW_DIR, 'turkey_ev_historical.csv'))
    historical = historical[['year', 'total_ev']]

    ibb = pd.read_csv(os.path.join(DATA_RAW_DIR, 'ibb_ev_yillik.csv'))
    tr_cols = [
        'TR - Otomobil ve Elektrik',
        'TR - Minibus ve Elektrik',
        'TR - Otobus ve Elektrik',
        'TR - Kamyonet ve Elektrik',
        'TR - Kamyon ve Elektrik',
    ]
    recent = pd.DataFrame({
        'year'     : ibb['Yil'].astype(int),
        'total_ev' : ibb[tr_cols].sum(axis=1).astype(int),
    })

    combined = pd.concat([historical, recent], ignore_index=True)
    combined = combined.sort_values('year').reset_index(drop=True)
    return combined


def load_istanbul_ev_series():
    """
    Builds the Istanbul EV time series from IBB raw data.
    Sums all electric vehicle types including motorcycles to stay consistent
    with N_BASE which is defined as Istanbul 2022 total EV count.

    Returns a DataFrame with columns: year, total_ev
    """
    ibb = pd.read_csv(os.path.join(DATA_RAW_DIR, 'ibb_ev_yillik.csv'))
    ist_cols = [
        'IST - Otomobil ve Elektrik',
        'IST - Minibus ve Elektrik',
        'IST - Otobus ve Elektrik',
        'IST - Kamyonet ve Elektrik',
        'IST - Kamyon ve Elektrik',
        'IST - Motosiklet ve Elektrik',
    ]
    series = pd.DataFrame({
        'year'     : ibb['Yil'].astype(int),
        'total_ev' : ibb[ist_cols].sum(axis=1).astype(int),
    })
    return series


def fit_turkey_curve():
    """
    Fits a logistic curve to the Turkey-wide EV time series (10 points).
    Returns the fitted parameters (K, r, t0).
    Used to validate the Istanbul fit against a longer adoption trend.
    """
    series = load_turkey_ev_series()
    years  = series['year'].values.astype(float)
    counts = series['total_ev'].values.astype(float)

    p0 = [3_000_000, 0.6, 2026.0]
    bounds = (
        [TURKEY_K_MIN, 0.1, 2020.0],
        [TURKEY_K_MAX, 3.0, 2035.0],
    )

    params, _ = curve_fit(logistic, years, counts, p0=p0,
                          bounds=bounds, maxfev=20000)
    return params


def fit_growth_curve():
    """
    Fits a logistic growth curve to Istanbul EV registration data.

    The fit is bounded so that K stays within a realistic policy range
    (ISTANBUL_K_MIN, ISTANBUL_K_MAX) derived from Turkey-wide projections:
    Climate Scorecard (2025) reports Turkey is expected to reach 20% or more
    EV penetration by 2034. Scaled to Istanbul's vehicle fleet share, this
    implies an Istanbul long-term EV ceiling between 0.5 and 1.5 million.

    Returns the fitted parameters (K, r, t0).
    """
    series = load_istanbul_ev_series()
    years  = series['year'].values.astype(float)
    counts = series['total_ev'].values.astype(float)

    # initial guess inside the bounded region
    p0 = [800_000, 0.6, 2026.0]
    bounds = (
        [ISTANBUL_K_MIN, 0.1, 2020.0],
        [ISTANBUL_K_MAX, 3.0, 2035.0],
    )

    params, _ = curve_fit(logistic, years, counts, p0=p0,
                          bounds=bounds, maxfev=20000)
    K, r, t0 = params

    print(f"Logistic curve fitted on Istanbul EV data ({len(series)} points):")
    print(f"  K  (carrying capacity) = {K:,.0f}")
    print(f"  r  (growth rate)       = {r:.4f}")
    print(f"  t0 (inflection year)   = {t0:.1f}")

    return K, r, t0


def get_growth_ratio(year, K, r, t0):
    """
    Computes the EV growth ratio for a given year relative to BASE_YEAR.
    r_y = logistic(year) / logistic(BASE_YEAR)
    """
    n_year = logistic(year, K, r, t0)
    n_base = logistic(BASE_YEAR, K, r, t0)
    return n_year / n_base


def get_ev_demand(year, theta=THETA_DEFAULT):
    """
    Computes charging demand q_d for each district.

    q_d(year, theta) = rho * theta * N_base * r_y * w_d

    The growth ratio r_y is derived from a bounded logistic fit on Istanbul
    data, with K bounds informed by Turkey-wide EV adoption projections.

    Returns a DataFrame with columns: district_id, name, demand
    """
    K, r, t0 = fit_growth_curve()
    r_y = get_growth_ratio(year, K, r, t0)

    zones = pd.read_csv(os.path.join(DATA_PROC_DIR, 'demand_zones.csv'))
    zones['demand'] = RHO * theta * N_BASE * r_y * zones['demand_weight']

    result = zones[['district_id', 'name', 'demand']].copy()

    print(f"\nEV demand for year {year} (theta={theta}):")
    print(f"  Growth ratio r_y     = {r_y:.4f}")
    print(f"  Total demand         = {result['demand'].sum():.2f}")
    print(result.head(5))

    return result


if __name__ == '__main__':
    print("=== Demand Model Test ===\n")
    demand = get_ev_demand(year=2026)
