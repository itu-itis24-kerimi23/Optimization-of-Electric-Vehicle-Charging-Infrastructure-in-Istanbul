import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (DATA_PROC_DIR, ALPHA, BETA, GAMMA, BUDGET)


def run_sensitivity_analysis(
    year=2025,
    theta=1.0,
    lambda_values=None,
    alpha=ALPHA,
    beta=BETA,
    gamma=GAMMA,
    budget=BUDGET
):
    """
    Runs sensitivity analysis on the overload penalty weight (lambda).
    Solves the MILP for each lambda value and records key metrics.

    Returns a DataFrame with results for each lambda value.
    """
    from milp_model import run_milp

    if lambda_values is None:
        lambda_values = [1, 5, 10, 20, 30, 50, 75, 100]

    results = []

    for lam in lambda_values:
        print(f"\n{'='*50}")
        print(f"Running MILP with λ = {lam}")
        print(f"{'='*50}")

        r = run_milp(
            year=year,
            theta=theta,
            alpha=alpha,
            beta=beta,
            gamma=gamma,
            lam=lam,
            budget=budget
        )

        # Total overload
        total_overload = sum(
            v for v in r['utilization'].values()
            if v > 1.0
        )

        results.append({
            'lambda'            : lam,
            'opened_stations'   : len(r['opened_candidates']),
            'expanded_stations' : len(r['expansions']),
            'total_unmet'       : r['total_unmet'],
            'total_investment'  : r['total_investment'],
            'objective'         : r['objective'],
            'status'            : r['status'],
        })

        print(f"  Opened   : {len(r['opened_candidates'])}")
        print(f"  Expanded : {len(r['expansions'])}")
        print(f"  Unmet    : {r['total_unmet']:.2f}")
        print(f"  Invest   : {r['total_investment']:,.0f} TL")

    df = pd.DataFrame(results)
    print("\n SENSITIVITY ANALYSIS RESULTS ")
    print(df.to_string(index=False))
    return df


def plot_sensitivity(df, save_path=None):
    """
    Plots sensitivity analysis results as a 2x2 figure.
    """
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle('Sensitivity Analysis on λ (Overload Penalty)', fontsize=14)

    # there will be 4 plots
    # Unmet Demand vs Lambda
    axes[0, 0].plot(df['lambda'], df['total_unmet'],
                    'o-', color='red', linewidth=2, markersize=6)
    axes[0, 0].set_xlabel('λ (Overload Penalty)')
    axes[0, 0].set_ylabel('Total Unmet Demand')
    axes[0, 0].set_title('Unmet Demand vs λ')
    axes[0, 0].grid(True, alpha=0.3)

    # Total Investment vs Lambda
    axes[0, 1].plot(df['lambda'], df['total_investment'] / 1e6,
                    'o-', color='blue', linewidth=2, markersize=6)
    axes[0, 1].set_xlabel('λ (Overload Penalty)')
    axes[0, 1].set_ylabel('Total Investment (Million TL)')
    axes[0, 1].set_title('Investment vs λ')
    axes[0, 1].grid(True, alpha=0.3)

    # Opened Stations vs Lambda
    axes[1, 0].bar(df['lambda'], df['opened_stations'].astype(int),
               color='green', alpha=0.7)
    axes[1, 0].set_xlabel('λ (Overload Penalty)')
    axes[1, 0].set_ylabel('Opened Stations')
    axes[1, 0].set_title('New Stations vs λ\n(0 across all λ — expansion preferred)')
    axes[1, 0].set_ylim(0, max(df['opened_stations'].max() + 1, 5))
    axes[1, 0].yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    axes[1, 0].grid(True, alpha=0.3)

    # Expanded Stations vs Lambda
    axes[1, 1].bar(df['lambda'], df['expanded_stations'],
                   color='blue', alpha=0.7)
    axes[1, 1].set_xlabel('λ (Overload Penalty)')
    axes[1, 1].set_ylabel('Expanded Stations')
    axes[1, 1].set_title('Expanded Stations vs λ')
    axes[1, 1].grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Plot saved to {save_path}")
    else:
        save_path = os.path.join(DATA_PROC_DIR, 'sensitivity_analysis.png')
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"Plot saved to {save_path}")

    plt.close()
    return save_path


if __name__ == '__main__':
    print("=== Sensitivity Analysis ===\n")
    print("Testing lambda values: 1, 5, 10, 20, 30, 50, 75, 100")
    print("This will run MILP 8 times — estimated time: 1-2 minutes\n")

    df = run_sensitivity_analysis(
        year=2025,
        theta=1.0,
        lambda_values=[1, 5, 10, 20, 30, 50, 75, 100]
    )

    path = plot_sensitivity(df)
    print(f"\nOpen plot: {path}")

    # Save results to csv
    csv_path = os.path.join(DATA_PROC_DIR, 'sensitivity_results.csv')
    df.to_csv(csv_path, index=False)
    print(f"Results saved: {csv_path}")