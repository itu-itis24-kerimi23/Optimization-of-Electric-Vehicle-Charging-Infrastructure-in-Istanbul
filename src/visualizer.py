import folium
import pandas as pd
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (DATA_PROC_DIR, MAP_CENTER, MAP_ZOOM, CIRCLE_SCALE)


def create_map(results, demand_df=None):
    """
    Creates a Folium map visualizing optimization results.

    Map elements:
    - Red circles    : existing stations (size = utilization)
    - Blue circles   : expanded existing stations
    - Green X marks  : newly opened candidate stations
    - Grey circles   : demand zones (size = demand weight)

    Parameters:
        results    : dict returned by run_milp() or run_greedy()
        demand_df  : DataFrame with district demand (optional)

    Returns:
        folium.Map object
    """

    # load data
    existing   = pd.read_csv(os.path.join(DATA_PROC_DIR, 'existing_stations.csv'))
    candidates = pd.read_csv(os.path.join(DATA_PROC_DIR, 'candidate_stations.csv'))
    zones      = pd.read_csv(os.path.join(DATA_PROC_DIR, 'demand_zones.csv'))

    # create base map
    m = folium.Map(
        location=MAP_CENTER,
        zoom_start=MAP_ZOOM,
        tiles='CartoDB positron'  # clean, minimal background
    )

    # add demand zones
    # Grey circles — size proportional to demand weight
    for _, zone in zones.iterrows():
        folium.CircleMarker(
            location=[zone['latitude'], zone['longitude']],
            radius=zone['demand_weight'] * 800,
            color='grey',
            fill=True,
            fill_color='grey',
            fill_opacity=0.2,
            popup=folium.Popup(
                f"<b>{zone['name']}</b><br>"
                f"Population: {zone['population']:,}<br>"
                f"Demand weight: {zone['demand_weight']:.4f}",
                max_width=200
            ),
            tooltip=zone['name']
        ).add_to(m)

    # add existing stations
    opened_set   = set(results.get('opened_candidates', []))
    expanded_set = set(results.get('expansions', {}).keys())
    utilization  = results.get('utilization', {})

    for _, station in existing.iterrows():
        sid  = station['station_id']
        util = utilization.get(sid, 0)

        # Size based on capacity, not utilization
        cap    = station['capacity'] + results['expansions'].get(sid, 0)
        radius = max(3, min(15, cap * 0.8))

        # Color: blue if expanded, red otherwise
        if sid in expanded_set:
            color  = 'blue'
            radius = max(6, min(15, cap * 0.8))
        else:
            color = 'red'

        folium.CircleMarker(
            location=[station['latitude'], station['longitude']],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.6,
            popup=folium.Popup(
                f"<b>{station['name']}</b><br>"
                f"ID: {sid}<br>"
                f"Capacity: {station['capacity']}<br>"
                f"Expansion: +{results['expansions'].get(sid, 0):.1f}<br>"
                f"Utilization: {util:.1%}",
                max_width=250
            ),
            tooltip=f"{sid} ({util:.0%})"
        ).add_to(m)

    # add opened candidate stations
    for _, cand in candidates.iterrows():
        cid = cand['candidate_id']
        if cid not in opened_set:
            continue

        util   = utilization.get(cid, 0)
        radius = max(5, util * CIRCLE_SCALE / 100)

        # Green x marker for newly opened stations
        folium.Marker(
            location=[cand['latitude'], cand['longitude']],
            icon=folium.DivIcon(
                html=f"""
                    <div style="
                        font-size: 16px;
                        font-weight: bold;
                        color: green;
                        text-shadow: 1px 1px 2px white;
                    ">✖</div>
                """,
                icon_size=(20, 20),
                icon_anchor=(10, 10)
            ),
            popup=folium.Popup(
                f"<b>NEW: {cand['name']}</b><br>"
                f"ID: {cid}<br>"
                f"County: {cand['county']}<br>"
                f"Capacity: {cand['max_capacity']}<br>"
                f"Utilization: {util:.1%}",
                max_width=250
            ),
            tooltip=f"NEW: {cid}"
        ).add_to(m)

    # add legend
    legend_html = """
    <div style="
        position: fixed;
        bottom: 30px; left: 30px;
        background: white;
        padding: 12px 16px;
        border-radius: 8px;
        border: 1px solid #ccc;
        font-size: 13px;
        z-index: 1000;
        box-shadow: 2px 2px 6px rgba(0,0,0,0.2);
        color: #333;
    ">
        <b>Legend</b><br>
        <span style="color:red">●</span> Existing station<br>
        <span style="color:blue">●</span> Expanded station<br>
        <span style="color:green">✖</span> New station<br>
        <span style="color:grey">●</span> Demand zone<br>
        <i>Circle size = utilization</i>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # summary box
    
    year       = results.get('year', '-')
    method     = results.get('status', '-')
    opened_n   = len(results.get('opened_candidates', []))
    expanded_n = len(results.get('expansions', {}))
    unmet      = results.get('total_unmet', 0)
    investment = results.get('total_investment', 0)

    summary_html = f"""
    <div style="
        position: fixed;
        top: 30px; right: 30px;
        background: white;
        padding: 12px 16px;
        border-radius: 8px;
        border: 1px solid #ccc;
        font-size: 14px;
        z-index: 1000;
        box-shadow: 2px 2px 6px rgba(0,0,0,0.2);
        color : #333;
    ">
        <h4 style="margin: 0 0 8px 0; color: #333;">Optimization Summary</h4>
        <b>Year:</b> {year}<br>
        <b>Method:</b> {method}<br>
        <b>Opened Stations:</b> {opened_n}<br>
        <b>Expanded Stations:</b> {expanded_n}<br>
        <b>Unmet Demand:</b> {unmet:.2f}<br>
        <b>Total Investment:</b> {investment:,.0f} TL
    </div>
    """

    m.get_root().html.add_child(folium.Element(summary_html))

    return m


def save_map(m, filename='map.html'):
    """Saves the map to data/processed/ directory."""
    output_path = os.path.join(DATA_PROC_DIR, filename)
    m.save(output_path)
    print(f"Map saved to {output_path}")
    return output_path


if __name__ == '__main__':
    print("=== Visualizer Test ===\n")

    import sys
    sys.path.append('src')
    from milp_model import run_milp
    from demand_model import get_ev_demand

    results    = run_milp(year=2025, theta=1.0)
    demand_df  = get_ev_demand(year=2025, theta=1.0)
    m          = create_map(results, demand_df)
    path       = save_map(m)
    print(f"Open in browser: {path}")