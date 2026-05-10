import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (DATA_RAW_DIR, DATA_PROC_DIR, BASE_YEAR,
                    N_BASE, RHO, THETA_DEFAULT)


# Logistic growth function
def logistic(t, K, r, t0):
    """
    Standard logistic growth curve.
    K  : carrying capacity (upper limit)
    r  : growth rate
    t0 : inflection point (year of fastest growth)
    """
    return K / (1 + np.exp(-r * (t - t0)))


# Fit the curve to IBB data
def fit_growth_curve():
    """
    Fits a logistic growth curve to Istanbul EV registration data.
    Returns the fitted parameters (K, r, t0).
    """
    # Load IBB yearly EV data
    df = pd.read_csv(os.path.join(DATA_RAW_DIR, 'ibb_ev_yillik.csv'))

    # Sum all electric vehicle types for Istanbul
    ev_cols = [
        'IST - Otomobil ve Elektrik',
        'IST - Minibus ve Elektrik',
        'IST - Otobus ve Elektrik',
        'IST - Kamyonet ve Elektrik',
        'IST - Kamyon ve Elektrik',
        'IST - Motosiklet ve Elektrik',
    ]
    df['total_ev'] = df[ev_cols].sum(axis=1)

    years  = df['Yil'].values.astype(float)
    counts = df['total_ev'].values.astype(float)

    # Initial guesses for K, r, t0
    p0 = [max(counts) * 10, 0.3, 2025.0]

    params, _ = curve_fit(logistic, years, counts, p0=p0, maxfev=10000)
    K, r, t0 = params

    print(f"Logistic curve fitted:")
    print(f"  K  (carrying capacity) = {K:,.0f}")
    print(f"  r  (growth rate)       = {r:.4f}")
    print(f"  t0 (inflection year)   = {t0:.1f}")

    return K, r, t0


# Compute growth ratio r_y
def get_growth_ratio(year, K, r, t0):
    """
    Computes the EV growth ratio for a given year relative to BASE_YEAR.
    r_y = logistic(year) / logistic(BASE_YEAR)
    """
    n_year = logistic(year,K, r, t0)
    n_base = logistic(BASE_YEAR, K, r, t0)
    ratio  = n_year / n_base
    return ratio


# Compute district level charging demand
def get_ev_demand(year, theta=THETA_DEFAULT):
    """
    Computes charging demand q_d for each district.

    q_d(y, theta) = rho * theta * N_base * r_y * w_d

    Returns a DataFrame with columns:
    district_id, name, demand
    """
    # Fit the curve and get growth ratio
    K, r, t0 = fit_growth_curve()
    r_y = get_growth_ratio(year, K, r, t0)

    # Load demand zones
    zones = pd.read_csv(os.path.join(DATA_PROC_DIR, 'demand_zones.csv'))

    # q_d = RHO * theta * N_BASE * r_y * w_d
    zones['demand'] = RHO * theta * N_BASE * r_y * zones['demand_weight']

    # Keep only relevant columns
    result = zones[['district_id', 'name', 'demand']].copy()

    print(f"\nEV demand for year {year} (theta={theta}):")
    print(f"  Growth ratio r_y     = {r_y:.4f}")
    print(f"  Total demand         = {result['demand'].sum():.2f}")
    print(result.head(5))

    return result


# test
if __name__ == '__main__':
    print("=== Demand Model Test ===\n")
    demand = get_ev_demand(year=2025)