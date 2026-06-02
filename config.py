import os

# folder paths
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
DATA_RAW_DIR   = os.path.join(BASE_DIR, "data", "raw")
DATA_PROC_DIR  = os.path.join(BASE_DIR, "data", "processed")

# objective function weights
# alpha: accessibility, beta: unmet demand, gamma: investment, lambda: overload
# these are default values, can be changed via Streamlit sliders
# Beta is scaled with the realistic 2026 demand level so the unmet penalty
# stays competitive against the marginal investment cost
ALPHA  = 1.0
BETA   = 50.0
GAMMA  = 1.0
LAMBDA = 50.0

# demand model parameters
BASE_YEAR   = 2022
N_BASE      = 21_522       # Istanbul 2022 total EV count (IBB data)
RHO = 0.20                 # Daily public charging rate per EV
                           # Estimated from EPDK Sep 2024 data:
                           # 23,377 sockets / 146,965 EVs = 0.159 base utilization
                           # Adjusted to 0.20 assuming ~1.3 average daily turnover per socket
                           # Source: EPDK Sarj Hizmeti Piyasasi Aylik Istatistikleri, Sep 2024
THETA_DEFAULT = 1.0        # Demand scaling factor (slider default)

# optimization parameters
BUDGET       = 150_000_000 # Total investment budget in TL
                           # Sized to address realistic 2026 demand projections
                           # (about 32K daily charging units) rather than the
                           # earlier underestimated demand level
D_MAX        = 20_000      # Maximum assignment distance in meters
BIG_M        = 1_000_000   # MILP big-M constant

# cost parameters, calibrated from EPDK and market data (2024-2025)
G_EXPANSION  = 35_000      # Cost of adding one AC socket to an existing station (TL)
                           # Source: Market price for AC charger installation 2024
F_OPENING    = 1_500_000   # Fixed cost of opening a new station (TL)
                           # Source: EPDK license fee 2025: 1,525,330 TL
H_CANDIDATE  = 60_000      # Cost of installing one socket at a candidate station (TL)
                           # Source: Average AC/DC charger installation (35,000-70,000 TL)

# capacity constraints
K_MAX_EXISTING   = 20      # Maximum total capacity at existing stations
K_MAX_CANDIDATE  = 15      # Maximum capacity at candidate stations

# growth curve parameters
# K bounds are used to keep the logistic fit in a realistic policy range
# Source: Climate Scorecard 2025 projects Turkey to reach 20% or more EV
# penetration by 2034 on a vehicle fleet of about 25M, implying a national
# EV ceiling around 5M and an Istanbul share (about 30% of the fleet) of
# roughly 1.5M

TURKEY_K_MIN = 1_500_000
TURKEY_K_MAX = 10_000_000

ISTANBUL_K_MIN = 500_000
ISTANBUL_K_MAX = 1_500_000

# observed Istanbul share of Turkey EV count, from IBB data (about 40% in 2024)
ISTANBUL_SHARE = 0.40

# years of scenario analysis
YEAR_MIN = 2022
YEAR_MAX = 2035
YEAR_DEFAULT = 2025

# solver settings
SOLVER_TIME_LIMIT = 120
SOLVER_GAP        = 0.05

# visual settings
MAP_CENTER      = [41.0082, 28.9784]
MAP_ZOOM        = 10
CIRCLE_SCALE    = 500
