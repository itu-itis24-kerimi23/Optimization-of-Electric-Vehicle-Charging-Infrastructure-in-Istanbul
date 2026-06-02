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

    The model uses a fraction-based formulation so that district demand q_d
    appears explicitly in the objective function and capacity constraints.

    Decision variables:
      x_i      additional capacity for existing station i
      y_j      binary, whether to open candidate station j
      z_j      installed capacity at opened candidate station j
      f_ds     fraction of district d demand assigned to service point s
      u_d_frac fraction of district d demand left unmet
      o_s      overload amount at station s

    Returns a dictionary with the optimization results.
    """

    # load processed data
    existing   = pd.read_csv(os.path.join(DATA_PROC_DIR, 'existing_stations.csv'))
    candidates = pd.read_csv(os.path.join(DATA_PROC_DIR, 'candidate_stations.csv'))
    zones      = pd.read_csv(os.path.join(DATA_PROC_DIR, 'demand_zones.csv'))
    dist_df    = pd.read_csv(os.path.join(DATA_PROC_DIR, 'distance_matrix.csv'),
                             index_col='district_id')

    # demand for the chosen year
    from demand_model import get_ev_demand
    demand_df = get_ev_demand(year, theta)
    demand = dict(zip(demand_df['district_id'], demand_df['demand']))
    total_demand = sum(demand.values())

    # index sets
    D = zones['district_id'].tolist()
    E = existing['station_id'].tolist()
    C = candidates['candidate_id'].tolist()
    S = E + C

    # capacity dictionaries
    K       = dict(zip(existing['station_id'], existing['capacity']))
    K_max_e = dict(zip(existing['station_id'], existing['max_capacity']))
    K_max_c = dict(zip(candidates['candidate_id'], candidates['max_capacity']))

    # cost dictionaries (uniform across stations, can be made station-specific)
    g = {i: G_EXPANSION for i in E}
    f = {j: F_OPENING   for j in C}
    h = {j: H_CANDIDATE for j in C}

    # accessibility normalization constant
    # C_max equals the total accessibility cost in the worst case where each
    # zone's demand is served by its farthest reachable point
    C_max = 0.0
    for d in D:
        max_dist = dist_df.loc[d].max()
        C_max += demand[d] * max_dist
    if C_max == 0:
        C_max = 1.0

    print(f"\nModel parameters:")
    print(f"  Zones: {len(D)}, Existing: {len(E)}, Candidates: {len(C)}")
    print(f"  Total demand : {total_demand:.2f}")
    print(f"  Budget       : {budget:,.0f} TL")
    print(f"  C_max        : {C_max:,.2f}")

    # build model
    prob = pulp.LpProblem("EV_Charging_Optimization", pulp.LpMinimize)

    # additional capacity at existing stations
    x = {i: pulp.LpVariable(f"x_{i}", lowBound=0) for i in E}

    # binary opening variable for candidate stations
    y = {j: pulp.LpVariable(f"y_{j}", cat='Binary') for j in C}

    # installed capacity at candidate stations
    z = {j: pulp.LpVariable(f"z_{j}", lowBound=0) for j in C}

    # fraction of district d demand assigned to service point s
    # only defined when the pair is within D_MAX (distance > 0 in the matrix)
    f_assign = {}
    for d in D:
        for s in S:
            dist = dist_df.loc[d, s] if s in dist_df.columns else 0
            if dist > 0:
                f_assign[d, s] = pulp.LpVariable(
                    f"f_{d}_{s}", lowBound=0, upBound=1
                )

    # fraction of district d demand left unmet
    u_frac = {d: pulp.LpVariable(f"u_{d}", lowBound=0, upBound=1) for d in D}

    # overload at service point s
    o = {s: pulp.LpVariable(f"o_{s}", lowBound=0) for s in S}

    n_vars = len(x) + len(y) + len(z) + len(f_assign) + len(u_frac) + len(o)
    print(f"  Variables    : {n_vars:,}")

    # objective function
    # demand q_d appears explicitly in accessibility and unmet terms

    # accessibility: demand-weighted travel distance
    accessibility = pulp.lpSum(
        demand[d] * dist_df.loc[d, s] * f_assign[d, s]
        for d in D for s in S
        if (d, s) in f_assign
    ) / C_max

    # unmet demand: total unmet across districts, normalized by total demand
    unmet = pulp.lpSum(demand[d] * u_frac[d] for d in D) / total_demand

    # investment cost normalized by budget
    investment = (
        pulp.lpSum(g[i] * x[i] for i in E) +
        pulp.lpSum(f[j] * y[j] for j in C) +
        pulp.lpSum(h[j] * z[j] for j in C)
    ) / budget

    # overload normalized by total demand
    overload = pulp.lpSum(o[s] for s in S) / total_demand

    prob += (alpha * accessibility +
             beta  * unmet +
             gamma * investment +
             lam   * overload), "Total_Cost"

    # constraints

    for d in D:
        # demand satisfaction: assigned fractions plus unmet fraction equals one
        prob += (
            pulp.lpSum(f_assign[d, s] for s in S if (d, s) in f_assign)
            + u_frac[d] == 1
        ), f"demand_satisfaction_{d}"

    for i in E:
        # capacity constraint at existing station i (demand-weighted assignments)
        prob += (
            pulp.lpSum(demand[d] * f_assign[d, i]
                       for d in D if (d, i) in f_assign)
            <= K[i] + x[i] + o[i]
        ), f"capacity_existing_{i}"

        # expansion is bounded by the difference between max and current capacity
        prob += x[i] <= K_max_e[i] - K[i], f"expansion_limit_{i}"

    for j in C:
        # capacity constraint at candidate station j (demand-weighted assignments)
        prob += (
            pulp.lpSum(demand[d] * f_assign[d, j]
                       for d in D if (d, j) in f_assign)
            <= z[j] + o[j]
        ), f"capacity_candidate_{j}"

        # capacity can only be installed if station is opened
        prob += z[j] <= K_max_c[j] * y[j], f"open_capacity_{j}"

        # candidate can only serve demand if opened
        prob += (
            pulp.lpSum(f_assign[d, j] for d in D if (d, j) in f_assign)
            <= BIG_M * y[j]
        ), f"open_demand_{j}"

    # total investment cannot exceed the available budget
    prob += (
        pulp.lpSum(g[i] * x[i] for i in E) +
        pulp.lpSum(f[j] * y[j] for j in C) +
        pulp.lpSum(h[j] * z[j] for j in C)
    ) <= budget, "budget_constraint"

    # solve with CBC
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
    # convert fractions back to absolute amounts (q_d * f_ds)
    unmet_absolute = {
        d: (pulp.value(u_frac[d]) or 0) * demand[d]
        for d in D
    }

    results = {
        'status'   : status,
        'objective': pulp.value(prob.objective),
        'year'     : year,
        'theta'    : theta,

        'opened_candidates': [
            j for j in C if pulp.value(y[j]) is not None
            and pulp.value(y[j]) > 0.5
        ],

        'expansions': {
            i: pulp.value(x[i])
            for i in E
            if pulp.value(x[i]) is not None and pulp.value(x[i]) > 0.01
        },

        'unmet_demand': unmet_absolute,
        'utilization': {},

        'total_unmet': sum(unmet_absolute.values()),
        'total_investment': (
            sum(G_EXPANSION * (pulp.value(x[i]) or 0) for i in E) +
            sum(F_OPENING   * (pulp.value(y[j]) or 0) for j in C) +
            sum(H_CANDIDATE * (pulp.value(z[j]) or 0) for j in C)
        ),
    }

    # utilization per station: assigned demand divided by available capacity
    for s in S:
        assigned = sum(
            demand[d] * (pulp.value(f_assign[d, s]) or 0)
            for d in D if (d, s) in f_assign
        )
        if s in E:
            capacity = K[s] + (pulp.value(x[s]) or 0)
        else:
            capacity = pulp.value(z[s]) or 0
        results['utilization'][s] = assigned / capacity if capacity > 0 else 0

    print(f"\n=== RESULTS ===")
    print(f"Opened stations  : {len(results['opened_candidates'])}")
    print(f"Expanded stations: {len(results['expansions'])}")
    print(f"Total unmet      : {results['total_unmet']:.2f} / {total_demand:.2f}")
    print(f"Total investment : {results['total_investment']:,.0f} TL")

    return results


if __name__ == '__main__':
    print("=== MILP Model Test ===")
    results = run_milp(year=2026, theta=1.0)
