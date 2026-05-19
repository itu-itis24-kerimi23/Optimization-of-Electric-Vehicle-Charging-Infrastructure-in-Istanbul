import pandas as pd
import numpy as np
import pulp
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (DATA_PROC_DIR, ALPHA, BETA, GAMMA, LAMBDA,
                    BUDGET, D_MAX, BIG_M, G_EXPANSION, F_OPENING,
                    H_CANDIDATE, K_MAX_EXISTING, K_MAX_CANDIDATE,
                    SOLVER_TIME_LIMIT, SOLVER_GAP)


def run_milp(year, theta=1.0, alpha=ALPHA, beta=BETA,
             gamma=GAMMA, lam=LAMBDA, budget=BUDGET):
    """
    Solves the EV charging infrastructure optimization problem.

    Parameters:
        year   : target year for demand estimation
        theta  : demand scaling factor
        alpha  : accessibility cost weight
        beta   : unmet demand penalty weight
        gamma  : investment cost weight
        lam    : overload penalty weight
        budget : total investment budget (TL)

    Returns:
        dict with optimization results
    """

    # load data
    existing   = pd.read_csv(os.path.join(DATA_PROC_DIR, 'existing_stations.csv'))
    candidates = pd.read_csv(os.path.join(DATA_PROC_DIR, 'candidate_stations.csv'))
    zones      = pd.read_csv(os.path.join(DATA_PROC_DIR, 'demand_zones.csv'))
    dist_df    = pd.read_csv(os.path.join(DATA_PROC_DIR, 'distance_matrix.csv'),
                             index_col='district_id')

    # compute demand
    from demand_model import get_ev_demand
    demand_df = get_ev_demand(year, theta)

    # Convert to dicts for fast lookup
    demand = dict(zip(demand_df['district_id'], demand_df['demand']))
    total_demand = sum(demand.values())

    # build index sets
    D = zones['district_id'].tolist()          # demand zones
    E = existing['station_id'].tolist()        # existing stations
    C = candidates['candidate_id'].tolist()    # candidate stations
    S = E + C                                  # all service points

    # Capacity dicts
    K   = dict(zip(existing['station_id'], existing['capacity']))
    K_max_e = dict(zip(existing['station_id'], existing['max_capacity']))
    K_max_c = dict(zip(candidates['candidate_id'], candidates['max_capacity']))

    # Cost dicts (using global values, can be station-specific later)
    g = {i: G_EXPANSION for i in E}   # expansion cost per unit
    f = {j: F_OPENING   for j in C}   # fixed opening cost
    h = {j: H_CANDIDATE for j in C}   # installation cost per unit

    # compute normalization constant
    # C_max: each zone's demand assigned to its farthest reachable point
    C_max = 0
    for d in D:
        max_dist = dist_df.loc[d].max()  # en uzak erişilebilir nokta
        C_max += demand[d] * max_dist
    if C_max == 0:
        C_max = 1

    print(f"  C_max (corrected) : {C_max:,.2f}")

    print(f"\nModel parameters:")
    print(f"  Zones: {len(D)}, Existing: {len(E)}, Candidates: {len(C)}")
    print(f"  Total demand : {total_demand:.2f}")
    print(f"  Budget       : {budget:,.0f} TL")
    print(f"  C_max        : {C_max:,.2f}")

    # create problem
    prob = pulp.LpProblem("EV_Charging_Optimization", pulp.LpMinimize)

    # decision variables

    # x_i: additional capacity for existing station i
    x = {i: pulp.LpVariable(f"x_{i}", lowBound=0) for i in E}

    # y_j: binary — open candidate station j?
    y = {j: pulp.LpVariable(f"y_{j}", cat='Binary') for j in C}

    # z_j: installed capacity at candidate station j
    z = {j: pulp.LpVariable(f"z_{j}", lowBound=0) for j in C}

    # a_ds: demand from zone d assigned to service point s
    a = {}
    for d in D:
        for s in S:
            dist = dist_df.loc[d, s] if s in dist_df.columns else 0
            if dist > 0:
                a[d, s] = pulp.LpVariable(f"a_{d}_{s}", lowBound=0)

    # u_d: unmet demand in zone d
    u = {d: pulp.LpVariable(f"u_{d}", lowBound=0) for d in D}

    # o_s: overload at service point s
    o = {s: pulp.LpVariable(f"o_{s}", lowBound=0) for s in S}

    print(f"  Variables    : {len(x)+len(y)+len(z)+len(a)+len(u)+len(o):,}")

    # objective function

    # accesibility cost
    accessibility = pulp.lpSum(
        dist_df.loc[d, s] * a[d, s]
        for d in D for s in S
        if (d, s) in a
    ) / C_max

    # unmet demand
    unmet = pulp.lpSum(u[d] for d in D) / total_demand

    # investment cost
    investment = (
        pulp.lpSum(g[i] * x[i] for i in E) +
        pulp.lpSum(f[j] * y[j] for j in C) +
        pulp.lpSum(h[j] * z[j] for j in C)
    ) / budget

    # overload penalty
    overload = pulp.lpSum(o[s] for s in S) / total_demand

    # Combined objective
    prob += (alpha * accessibility +
             beta  * unmet +
             gamma * investment +
             lam   * overload), "Total_Cost"

    # constraints

    for d in D:
        #demand satisfaction
        
        prob += pulp.lpSum(a[d, s] for s in S if (d, s) in a) + u[d] == demand[d], f"demand_satisfaction_{d}"

    for i in E:
        # Capacity constraint for existing stations
        prob += pulp.lpSum(a[d, i] for d in D if (d, i) in a) <= K[i] + x[i] + o[i], f"capacity_existing_{i}"

        # Expansion limit for existing stations
        prob += x[i] <= K_max_e[i] - K[i], f"expansion_limit_{i}"

    for j in C:
        # capacity constraint for candidate stations
        prob += (
            pulp.lpSum(a[d, j] for d in D if (d, j) in a) <= z[j] + o[j]
        ), f"capacity_candidate_{j}"

        # Capacity only if opened
        prob += z[j] <= K_max_c[j] * y[j], f"open_capacity_{j}"

        # Demand only if opened
        prob += (
            pulp.lpSum(a[d, j] for d in D if (d, j) in a) <= BIG_M * y[j]
        ), f"open_demand_{j}"

    # Budget constraint
    prob += (
        pulp.lpSum(g[i] * x[i] for i in E) + 
        pulp.lpSum(f[j] * y[j] for j in C) + 
        pulp.lpSum(h[j] * z[j] for j in C)
    ) <= budget, "budget_constraint"

    # solve
    print("\nSolving...")
    solver = pulp.PULP_CBC_CMD(
        timeLimit=SOLVER_TIME_LIMIT,
        gapRel=SOLVER_GAP,
        msg=1
    )
    prob.solve(solver)

    status = pulp.LpStatus[prob.status]
    print(f"Status: {status}")
    print(f"Objective: {pulp.value(prob.objective):.6f}")

    # extract results
    results = {
        'status'   : status,
        'objective': pulp.value(prob.objective),
        'year'     : year,
        'theta'    : theta,

        # Which candidates to open
        'opened_candidates': [
            j for j in C if pulp.value(y[j]) is not None
            and pulp.value(y[j]) > 0.5
        ],

        # Capacity expansions for existing stations
        'expansions': {
            i: pulp.value(x[i])
            for i in E
            if pulp.value(x[i]) is not None and pulp.value(x[i]) > 0.01
        },

        # Unmet demand per zone
        'unmet_demand': {
            d: pulp.value(u[d])
            for d in D
            if pulp.value(u[d]) is not None
        },

        # Utilization per station
        'utilization': {},

        'total_unmet'     : sum(pulp.value(u[d]) or 0 for d in D),
        'total_investment': (
            sum(G_EXPANSION * (pulp.value(x[i]) or 0) for i in E) +
            sum(F_OPENING   * (pulp.value(y[j]) or 0) for j in C) +
            sum(H_CANDIDATE * (pulp.value(z[j]) or 0) for j in C)
        ),
    }

    # Compute utilization for each station
    for s in S:
        assigned = sum(
            pulp.value(a[d, s]) or 0
            for d in D if (d, s) in a
        )
        if s in E:
            capacity = K[s] + (pulp.value(x[s]) or 0)
        else:
            capacity = pulp.value(z[s]) or 0
        results['utilization'][s] = assigned / capacity if capacity > 0 else 0

    # Print summary
    print(f"\n=== RESULTS ===")
    print(f"Opened stations  : {len(results['opened_candidates'])}")
    print(f"Expanded stations: {len(results['expansions'])}")
    print(f"Total unmet      : {results['total_unmet']:.2f} / {total_demand:.2f}")
    print(f"Total investment : {results['total_investment']:,.0f} TL")

    return results


if __name__ == '__main__':
    print("=== MILP Model Test ===")
    results = run_milp(year=2025, theta=1.0)