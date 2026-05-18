# constant parameters defined here

import os

# folder paths
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
DATA_RAW_DIR   = os.path.join(BASE_DIR, "data", "raw")
DATA_PROC_DIR  = os.path.join(BASE_DIR, "data", "processed")

# objective function weights
# α (access), β (unmet demand), γ (cost of investment), λ (overrun penalty)
# These values ​​can be changed with the slider in Streamlit, these are the default values.

ALPHA  = 1.0
BETA   = 20.0
GAMMA  = 1.0
LAMBDA = 50.0 

# demand model parameters
BASE_YEAR   = 2022     # The year Nbase is based on
N_BASE      = 21_522  # 2022 Istanbul EV count (IBB data)
RHO = 0.20  # Daily public charging rate per EV
            # Estimated from EPDK data (Sep 2024):
            # 23,377 sockets / 146,965 EVs = 0.159 base rate
            # Adjusted to 0.20 assuming ~1.3 average daily utilization per socket
            # Source: EPDK Sarj Hizmeti Piyasasi Aylik Istatistikleri, Sep 2024
THETA_DEFAULT = 1.0    # Demand scaling parameter (slider default)

# optimization parameteres
BUDGET       = 50_000_000   # Total investment budget (TL)
D_MAX        = 20_000       # Maximum deployment distance
BIG_M        = 1_000_000    # MILP big-M constant

# cost parameters
G_EXPANSION  = 50_000    # Cost of adding 1 unit of capacity to the existing station (TL)
F_OPENING    = 500_000   # Fixed cost of opening a new station (TL)
H_CANDIDATE  = 80_000    # Cost of establishing 1 unit of capacity at the new station (TL)

# capacity constraints
K_MAX_EXISTING   = 20   # Maximum total capacity unit at existing stations
K_MAX_CANDIDATE  = 15   # Maximum capacity unit at candidate stations

# Years of scenario analysis
YEAR_MIN = 2022
YEAR_MAX = 2035
YEAR_DEFAULT = 2026

# solver settings
SOLVER_TIME_LIMIT = 120   # seconds (CBC solver time limit)
SOLVER_GAP        = 0.05  # 5% optimality gap, tolerance for major problems.

# visual settings
MAP_CENTER      = [41.0082, 28.9784]   # center of Istanbul
MAP_ZOOM        = 10
CIRCLE_SCALE    = 500    # The red circle represents the scaling factor (utilization → radius).