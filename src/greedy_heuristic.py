import pandas as pd
import numpy as np
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (DATA_PROC_DIR, BUDGET, G_EXPANSION, F_OPENING,
                    H_CANDIDATE, K_MAX_EXISTING)


def run_greedy(year, theta=1.0, budget=BUDGET):
    """
    Greedy heuristic for EV charging infrastructure optimization.

    Opens candidate stations in order of cost-effectiveness
    (demand covered per unit investment cost) until budget is exhausted.
    Remaining budget is used to expand existing stations.

    Returns a dict with the same structure as run_milp() for comparison.
    """

    # load data
    existing   = pd.read_csv(os.path.join(DATA_PROC_DIR, 'existing_stations.csv'))
    candidates = pd.read_csv(os.path.join(DATA_PROC_DIR, 'candidate_stations.csv'))
    zones      = pd.read_csv(os.path.join(DATA_PROC_DIR, 'demand_zones.csv'))
    dist_df    = pd.read_csv(os.path.join(DATA_PROC_DIR, 'distance_matrix.csv'),
                             index_col='district_id')

    # compute demand
    from demand_model import get_ev_demand
    demand_df  = get_ev_demand(year, theta)
    demand     = dict(zip(demand_df['district_id'], demand_df['demand']))
    total_demand = sum(demand.values())

    # build index
    D = zones['district_id'].tolist()
    E = existing['station_id'].tolist()
    C = candidates['candidate_id'].tolist()

    K = dict(zip(existing['station_id'], existing['capacity']))
    K_max_e = dict(zip(existing['station_id'], existing['max_capacity']))
    K_max_c = dict(zip(candidates['candidate_id'], candidates['max_capacity']))

    # scores of each candidate

    scores = []
    for j in C:
        # Demand reachable from this candidate 
        reachable_demand = sum(
            demand[d]
            for d in D
            if dist_df.loc[d, j] > 0  # dist > 0 means within D_MAX
        )

        # Total cost to open with max capacity
        total_cost = F_OPENING + H_CANDIDATE * K_max_c[j]

        # Cost-effectiveness score
        if total_cost > 0:
            score = reachable_demand / total_cost
        else:
            score = 0

        scores.append({
            'candidate_id'    : j,
            'reachable_demand': reachable_demand,
            'total_cost'      : total_cost,
            'max_capacity'    : K_max_c[j],
            'score'           : score
        })

    # Sort by score descending
    scores_df = pd.DataFrame(scores).sort_values('score', ascending=False)

    # greedy selection
    remaining_budget = budget
    opened = []       # list of opened candidate_ids
    installed = {}    # candidate_id -> installed capacity

    for _, row in scores_df.iterrows():
        cost = row['total_cost']

        # YOUR CODE HERE
        # Hint: Eğer remaining_budget >= cost ise:
        #   - opened listesine ekle
        #   - installed dict'ine max_capacity'yi kaydet
        #   - remaining_budget'tan cost'u çıkar
        # Değilse: atla (continue)
        if remaining_budget >= cost:
            opened.append(row['candidate_id'])
            installed[row['candidate_id']] = row['max_capacity']
            remaining_budget -= cost
        else:
            continue

    print(f"Greedy opened {len(opened)} candidate stations")
    print(f"Remaining budget for expansion: {remaining_budget:,.0f} TL")

    # expand existing stations with remaining budget
    # Use remaining budget to expand existing stations
    # Expand cheapest-to-expand stations first

    expansions = {}

    # Sort existing by expansion room (most room first)
    existing['expansion_room'] = existing['max_capacity'] - existing['capacity']
    expandable = existing[existing['expansion_room'] > 0].sort_values(
        'expansion_room', ascending=False
    )

    for _, row in expandable.iterrows():
        if remaining_budget <= 0:
            break

        i = row['station_id']
        room = row['expansion_room']

        max_units = int(remaining_budget // G_EXPANSION)
        actual_units = min(room, max_units)
        
        if actual_units > 0:
            expansions[i] = actual_units
            remaining_budget -= actual_units * G_EXPANSION

    print(f"Greedy expanded {len(expansions)} existing stations")

    # compute results

    # Build capacity dict for all open stations
    capacity = {}
    for i in E:
        capacity[i] = K[i] + expansions.get(i, 0)
    for j in opened:
        capacity[j] = installed.get(j, 0)

    # Assign demand greedily: nearest station first
    unmet_demand = {}
    utilization  = {s: 0.0 for s in list(E) + opened}  

    for d in D:
        remaining = demand[d]

        reachable = [
            (s, dist_df.loc[d, s])
            for s in (E + opened)
            if dist_df.loc[d, s] > 0 and capacity.get(s, 0) > 0
        ]
        reachable.sort(key=lambda x: x[1])

        for s, dist in reachable:
            if remaining <= 0:
                break
            available = max(0, capacity[s] - utilization[s])  
            assigned  = min(remaining, available)
            utilization[s] += assigned                         
            remaining -= assigned

        unmet_demand[d] = max(0, remaining)

    utilization = {
        s: utilization[s] / capacity[s] if capacity.get(s, 0) > 0 else 0
        for s in utilization
    }

    total_unmet = sum(unmet_demand.values())
    total_investment = (
        sum(F_OPENING + H_CANDIDATE * installed.get(j, 0) for j in opened) +
        sum(G_EXPANSION * v for v in expansions.values())
    )

    # return results
    results = {
        'status'            : 'Greedy',
        'year'              : year,
        'theta'             : theta,
        'opened_candidates' : opened,
        'expansions'        : expansions,
        'unmet_demand'      : unmet_demand,
        'utilization'       : utilization,
        'total_unmet'       : total_unmet,
        'total_investment'  : total_investment,
    }

    print(f"\n=== GREEDY RESULTS ===")
    print(f"Opened stations  : {len(opened)}")
    print(f"Expanded stations: {len(expansions)}")
    print(f"Total unmet      : {total_unmet:.2f} / {total_demand:.2f}")
    print(f"Total investment : {total_investment:,.0f} TL")

    return results


if __name__ == '__main__':
    print("=== Greedy Heuristic Test ===\n")
    results = run_greedy(year=2025, theta=1.0)