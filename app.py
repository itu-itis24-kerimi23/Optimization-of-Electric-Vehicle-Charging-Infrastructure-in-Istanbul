import streamlit as st
import sys
import os
import pandas as pd
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from streamlit_folium import st_folium
from milp_model import run_milp
from greedy_heuristic import run_greedy
from visualizer import create_map
from demand_model import get_ev_demand
from config import (YEAR_MIN, YEAR_MAX, YEAR_DEFAULT,
                    ALPHA, BETA, GAMMA, LAMBDA,
                    BUDGET, THETA_DEFAULT)

# page config
st.set_page_config(
    page_title="Istanbul EV Charging Optimizer",
    layout="wide"
)

# sessions state
# Keep the results in memory — they won't get lost even if the slider changes.
if 'milp_results' not in st.session_state:
    st.session_state.milp_results = None
if 'greedy_results' not in st.session_state:
    st.session_state.greedy_results = None
if 'demand_df' not in st.session_state:
    st.session_state.demand_df = None
if 'total_demand' not in st.session_state:
    st.session_state.total_demand = None

# title
st.title("Istanbul EV Charging Infrastructure Optimizer")
st.markdown("Optimize the allocation of EV charging capacity across Istanbul's districts.")

# sidebar
st.sidebar.header("Parameters")

year = st.sidebar.slider(
    "Target Year",
    min_value=YEAR_MIN,
    max_value=YEAR_MAX,
    value=YEAR_DEFAULT,
    step=1
)

theta = st.sidebar.slider(
    "Demand Scaling (θ)",
    min_value=0.5,
    max_value=3.0,
    value=float(THETA_DEFAULT),
    step=0.1,
    help="Scale factor for charging demand. θ=1.0 is the baseline scenario."
)

budget = st.sidebar.slider(
    "Budget (Million TL)",
    min_value=10,
    max_value=200,
    value=int(BUDGET / 1_000_000),
    step=10
) * 1_000_000

st.sidebar.markdown("---")
st.sidebar.subheader("Objective Weights")

alpha = st.sidebar.slider("α — Accessibility",    0.0, 5.0,   float(ALPHA),  0.5)
beta  = st.sidebar.slider("β — Unmet Demand",     0.0, 30.0,  float(BETA),   0.5)
gamma = st.sidebar.slider("γ — Investment Cost",  0.0, 5.0,   float(GAMMA),  0.5)
lam   = st.sidebar.slider("λ — Overload Penalty", 0.0, 100.0, float(LAMBDA), 5.0)

st.sidebar.markdown("---")

method = st.sidebar.radio(
    "Optimization Method",
    ["MILP (Optimal)", "Greedy (Fast)", "Both (Compare)"],
    index=0
)

# demand preview
st.subheader(f"Demand Forecast — {year}")

demand_df    = get_ev_demand(year, theta)
total_demand = demand_df['demand'].sum()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Demand", f"{total_demand:.1f} units")
with col2:
    st.metric("Target Year", year)
with col3:
    st.metric("Demand Scale (θ)", theta)

chart_df = demand_df.set_index('name')['demand'].sort_values(
    ascending=False).reset_index()
chart_df.columns = ['District', 'Demand']
st.dataframe(chart_df, use_container_width=True, height=250)

st.markdown("---")

# run button
run = st.sidebar.button("Optimize!", use_container_width=True)

if run:
    # clear previous results
    st.session_state.milp_results   = None
    st.session_state.greedy_results = None

    if method in ["MILP (Optimal)", "Both (Compare)"]:
        with st.spinner("Running MILP optimization..."):
            st.session_state.milp_results = run_milp(
                year=year, theta=theta,
                alpha=alpha, beta=beta,
                gamma=gamma, lam=lam,
                budget=budget
            )
        st.success("MILP optimization complete!")

    if method in ["Greedy (Fast)", "Both (Compare)"]:
        with st.spinner("🔄 Running Greedy heuristic..."):
            st.session_state.greedy_results = run_greedy(
                year=year, theta=theta,
                budget=budget
            )
        st.success("Greedy optimization complete!")

    # save demand
    st.session_state.demand_df    = demand_df
    st.session_state.total_demand = total_demand

# results
milp_results   = st.session_state.milp_results
greedy_results = st.session_state.greedy_results
saved_demand   = st.session_state.demand_df

if milp_results or greedy_results:

    st.subheader("Optimization Results")

    if method == "Both (Compare)" and milp_results and greedy_results:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### MILP (Optimal)")
            st.metric("Opened Stations",
                      len(milp_results['opened_candidates']))
            st.metric("Expanded Stations",
                      len(milp_results['expansions']))
            st.metric("Unmet Demand",
                      f"{milp_results['total_unmet']:.1f} / {st.session_state.total_demand:.1f}")
            st.metric("Total Investment",
                      f"{milp_results['total_investment']:,.0f} TL")
        with col2:
            st.markdown("### Greedy (Fast)")
            st.metric("Opened Stations",
                      len(greedy_results['opened_candidates']))
            st.metric("Expanded Stations",
                      len(greedy_results['expansions']))
            st.metric("Unmet Demand",
                      f"{greedy_results['total_unmet']:.1f} / {st.session_state.total_demand:.1f}")
            st.metric("Total Investment",
                      f"{greedy_results['total_investment']:,.0f} TL")

        gap = greedy_results['total_unmet'] - milp_results['total_unmet']
        gap_pct = gap / milp_results['total_unmet'] * 100 if milp_results['total_unmet'] > 0 else 0
        st.info(f"MILP reduces unmet demand by **{gap:.1f} units** ({gap_pct:.1f}%) vs Greedy.")

    elif milp_results:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Opened Stations",  len(milp_results['opened_candidates']))
        with col2:
            st.metric("Expanded Stations", len(milp_results['expansions']))
        with col3:
            st.metric("Unmet Demand", f"{milp_results['total_unmet']:.1f}")
        with col4:
            st.metric("Investment", f"{milp_results['total_investment']/1e6:.1f}M TL")

    elif greedy_results:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Opened Stations",  len(greedy_results['opened_candidates']))
        with col2:
            st.metric("Expanded Stations", len(greedy_results['expansions']))
        with col3:
            st.metric("Unmet Demand", f"{greedy_results['total_unmet']:.1f}")
        with col4:
            st.metric("Investment", f"{greedy_results['total_investment']/1e6:.1f}M TL")

    # maps
    st.subheader("Result Map")

    if method == "Both (Compare)" and milp_results and greedy_results:
        tab1, tab2 = st.tabs(["MILP Map", "Greedy Map"])
        with tab1:
            m = create_map(milp_results, saved_demand)
            st_folium(m, width=None, height=550, returned_objects=[])
        with tab2:
            m = create_map(greedy_results, saved_demand)
            st_folium(m, width=None, height=550, returned_objects=[])

    elif milp_results:
        m = create_map(milp_results, saved_demand)
        st_folium(m, width=None, height=550, returned_objects=[])

    elif greedy_results:
        m = create_map(greedy_results, saved_demand)
        st_folium(m, width=None, height=550, returned_objects=[])

    # unmet demand table
    st.subheader("Unmet Demand by District")
    zones    = pd.read_csv('data/processed/demand_zones.csv')
    unmet_df = zones[['district_id', 'name', 'demand_weight']].copy()
    unmet_df = unmet_df.merge(
        saved_demand[['district_id', 'demand']], on='district_id'
    )

    if milp_results:
        unmet_df['milp_unmet'] = unmet_df['district_id'].map(
            milp_results['unmet_demand']).fillna(0).round(2)
    if greedy_results:
        unmet_df['greedy_unmet'] = unmet_df['district_id'].map(
            greedy_results['unmet_demand']).fillna(0).round(2)

    unmet_df = unmet_df.sort_values('demand', ascending=False)
    st.dataframe(unmet_df, use_container_width=True)

    # Expanded stations table
    st.subheader("Expanded Existing Stations")

    if method == "Both (Compare)" and milp_results and greedy_results:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**MILP**")
            if milp_results['expansions']:
                exp_df = pd.DataFrame([
                    {'Station ID': sid, 'Added Capacity': val}
                    for sid, val in milp_results['expansions'].items()
                ]).sort_values('Added Capacity', ascending=False)
                st.dataframe(exp_df, use_container_width=True)
            else:
                st.write("No expansions.")

        with col2:
            st.markdown("**Greedy**")
            if greedy_results['expansions']:
                exp_df = pd.DataFrame([
                    {'Station ID': sid, 'Added Capacity': val}
                    for sid, val in greedy_results['expansions'].items()
                ]).sort_values('Added Capacity', ascending=False)
                st.dataframe(exp_df, use_container_width=True)
            else:
                st.write("No expansions.")

    else:
        active_results = milp_results if milp_results else greedy_results
        if active_results and active_results['expansions']:
            exp_df = pd.DataFrame([
                {'Station ID': sid, 'Added Capacity': val}
                for sid, val in active_results['expansions'].items()
            ]).sort_values('Added Capacity', ascending=False)
            st.dataframe(exp_df, use_container_width=True)
        else:
            st.write("No expansions.")

    # Opened candidates table
    st.subheader("Newly Opened Stations")
    cands = pd.read_csv('data/processed/candidate_stations.csv')

    if method == "Both (Compare)" and milp_results and greedy_results:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**MILP**")
            if milp_results['opened_candidates']:
                opened_df = cands[
                    cands['candidate_id'].isin(milp_results['opened_candidates'])
                ][['candidate_id', 'name', 'county', 'max_capacity']]
                st.dataframe(opened_df, use_container_width=True)
            else:
                st.write("No new stations.")

        with col2:
            st.markdown("**Greedy**")
            if greedy_results['opened_candidates']:
                opened_df = cands[
                    cands['candidate_id'].isin(greedy_results['opened_candidates'])
                ][['candidate_id', 'name', 'county', 'max_capacity']]
                st.dataframe(opened_df, use_container_width=True)
            else:
                st.write("No new stations.")

    else:
        active_results = milp_results if milp_results else greedy_results
        if active_results and active_results['opened_candidates']:
            opened_df = cands[
                cands['candidate_id'].isin(active_results['opened_candidates'])
            ][['candidate_id', 'name', 'county', 'max_capacity']]
            st.dataframe(opened_df, use_container_width=True)
        else:
            st.write("No new stations.")
    
    # sensitivity analysis
    if method != "Greedy (Fast)":
        st.subheader("Sensitivity Analysis on λ")

        sens_csv  = 'data/processed/sensitivity_results.csv'
        sens_img  = 'data/processed/sensitivity_analysis.png'

        if os.path.exists(sens_csv) and os.path.exists(sens_img):
            col1, col2 = st.columns([1, 2])

            with col1:
                st.markdown("**Results Table**")
                sens_df = pd.read_csv(sens_csv)
                sens_df['total_investment'] = (
                    sens_df['total_investment'] / 1e6
                ).round(1)
                sens_df = sens_df.rename(columns={
                    'lambda'            : 'λ',
                    'opened_stations'   : 'Opened',
                    'expanded_stations' : 'Expanded',
                    'total_unmet'       : 'Unmet',
                    'total_investment'  : 'Invest (M TL)',
                    'objective'         : 'Objective',
                    'status'            : 'Status'
                })
                st.dataframe(sens_df, use_container_width=True)
                st.caption(
                    "Critical threshold at λ=10: "
                    "model starts investing above this value."
                )

            with col2:
                st.markdown("**Analysis Plot**")
                st.image(sens_img, use_container_width=True)

        else:
            st.info(
                "Sensitivity analysis not yet run. "
                "Execute: `python src/sensitivity_analysis.py`"
            )
    else:
        st.info("Sensitivity analysis is only available for MILP.")

else:
    st.info("Set parameters in the sidebar and click **Optimize!** to run.")