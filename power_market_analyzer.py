# =====================================================================
# EUROPEAN POWER MARKET ANALYZER - OPTIMIZED V2.0
# Author: Felix Okumo
# Date: January 2026
# Description: Automated merit order dispatch and scenario analysis
# =====================================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import os
import warnings
warnings.filterwarnings('ignore')

# Set display options
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_rows', 100)

print("="*70)
print("⚡ EUROPEAN POWER MARKET ANALYZER V2.0")
print("="*70)
print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# ===== CONFIGURATION & PATHS =====

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)

DATA_DIR = os.path.join(PROJECT_DIR, 'Data')
OUTPUT_DIR = os.path.join(PROJECT_DIR, 'Outputs')
CHARTS_DIR = os.path.join(OUTPUT_DIR, 'charts')

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CHARTS_DIR, exist_ok=True)

print(f"📁 Project Directory: {PROJECT_DIR}")
print(f"📁 Data Directory: {DATA_DIR}")
print(f"📁 Output Directory: {OUTPUT_DIR}")
print()

# ===== DATA LOADING FUNCTIONS =====

def load_plant_database():
    """Load power plant database with robust encoding handling"""
    print("📥 Loading Plant Database...")
    
    file_path = os.path.join(DATA_DIR, 'German_Power_Plant_Database_2024_CORRECTED.csv')
    
    try:
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        plants_df = None
        
        for encoding in encodings:
            try:
                plants_df = pd.read_csv(file_path, encoding=encoding)
                print(f"   ✅ Successfully loaded with {encoding} encoding")
                break
            except UnicodeDecodeError:
                continue
        
        if plants_df is None:
            raise ValueError("Could not read file with any standard encoding")
        
        plants_df.columns = plants_df.columns.str.strip()
        
        print(f"   ✅ Loaded {len(plants_df)} power plants")
        print(f"   💪 Total capacity: {plants_df['Capacity_MW'].sum():,.0f} MW")
        print()
        
        return plants_df
    
    except FileNotFoundError:
        print(f"   ❌ ERROR: Could not find file at: {file_path}")
        return None
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
        return None


def load_scenarios():
    """Load market scenarios"""
    print("📥 Loading Market Scenarios...")
    
    file_path = os.path.join(DATA_DIR, 'Market_Scenarios_2024.csv')
    
    try:
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        scenarios_df = None
        
        for encoding in encodings:
            try:
                scenarios_df = pd.read_csv(file_path, encoding=encoding)
                print(f"   ✅ Successfully loaded with {encoding} encoding")
                break
            except UnicodeDecodeError:
                continue
        
        if scenarios_df is None:
            raise ValueError("Could not read file with any standard encoding")
        
        scenarios_df.columns = scenarios_df.columns.str.strip()
        
        print(f"   ✅ Loaded {len(scenarios_df)} scenarios")
        print()
        
        return scenarios_df
    
    except FileNotFoundError:
        print(f"   ❌ ERROR: Could not find file at: {file_path}")
        return None
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
        return None


def display_data_summary(plants_df, scenarios_df):
    """Display comprehensive data summary"""
    print("="*70)
    print("📊 DATA SUMMARY")
    print("="*70)
    
    if plants_df is not None:
        print("\n🏭 POWER PLANT DATABASE:")
        print(f"   Total Plants: {len(plants_df)}")
        print(f"   Total Capacity: {plants_df['Capacity_MW'].sum():,.0f} MW")
        
        if 'Plant_Type' in plants_df.columns:
            print("\n   Capacity by Plant Type:")
            capacity_by_type = plants_df.groupby('Plant_Type')['Capacity_MW'].sum().sort_values(ascending=False)
            for plant_type, capacity in capacity_by_type.items():
                percentage = (capacity / plants_df['Capacity_MW'].sum()) * 100
                print(f"      {plant_type:15s}: {capacity:8,.0f} MW ({percentage:5.1f}%)")
        
        if 'Technology' in plants_df.columns:
            print("\n   Capacity by Technology:")
            capacity_by_tech = plants_df.groupby('Technology')['Capacity_MW'].sum().sort_values(ascending=False)
            for tech, capacity in capacity_by_tech.items():
                percentage = (capacity / plants_df['Capacity_MW'].sum()) * 100
                print(f"      {tech:20s}: {capacity:8,.0f} MW ({percentage:5.1f}%)")
    
    if scenarios_df is not None:
        print("\n📈 MARKET SCENARIOS:")
        print(f"   Number of Scenarios: {len(scenarios_df)}")
        print(f"   Demand Range: {scenarios_df['Demand_MW'].min():,.0f} - {scenarios_df['Demand_MW'].max():,.0f} MW")
        
        if 'Carbon_Price_EUR_ton' in scenarios_df.columns:
            print(f"   Carbon Price Range: €{scenarios_df['Carbon_Price_EUR_ton'].min():.0f} - €{scenarios_df['Carbon_Price_EUR_ton'].max():.0f}/ton")
        
        if 'Wind_Availability_Percent' in scenarios_df.columns:
            print(f"   Wind Availability: {scenarios_df['Wind_Availability_Percent'].min():.0f}% - {scenarios_df['Wind_Availability_Percent'].max():.0f}%")
        
        if 'Solar_Availability_Percent' in scenarios_df.columns:
            print(f"   Solar Availability: {scenarios_df['Solar_Availability_Percent'].min():.0f}% - {scenarios_df['Solar_Availability_Percent'].max():.0f}%")
    
    print("\n" + "="*70)
    print()


# ===== MERIT ORDER CALCULATION =====

def calculate_srmc(plant_row, carbon_price):
    """Calculate Short Run Marginal Cost (SRMC)"""
    fuel_cost = plant_row['Fuel_Cost_EUR_MWh']
    co2_emissions = plant_row['CO2_Emissions_t_MWh']
    variable_om = plant_row['Variable_OM_EUR_MWh']
    
    carbon_cost = carbon_price * co2_emissions
    srmc = fuel_cost + carbon_cost + variable_om
    
    return srmc


def apply_renewable_availability(plants_df, wind_avail_pct, solar_avail_pct):
    """Adjust renewable capacity based on availability"""
    plants_adjusted = plants_df.copy()
    
    plants_adjusted['Available_Capacity_MW'] = plants_adjusted['Capacity_MW'].copy()
    
    # Apply wind availability
    wind_mask = plants_adjusted['Technology'] == 'Wind'
    plants_adjusted.loc[wind_mask, 'Available_Capacity_MW'] = \
        plants_adjusted.loc[wind_mask, 'Capacity_MW'] * (wind_avail_pct / 100.0)
    
    # Apply solar availability
    solar_mask = plants_adjusted['Technology'] == 'Solar'
    plants_adjusted.loc[solar_mask, 'Available_Capacity_MW'] = \
        plants_adjusted.loc[solar_mask, 'Capacity_MW'] * (solar_avail_pct / 100.0)
    
    # Apply plant-specific availability for conventional plants
    conventional_mask = ~(wind_mask | solar_mask)
    plants_adjusted.loc[conventional_mask, 'Available_Capacity_MW'] = \
        plants_adjusted.loc[conventional_mask, 'Capacity_MW'] * \
        (plants_adjusted.loc[conventional_mask, 'Availability_Percent'] / 100.0)
    
    return plants_adjusted


def run_merit_order_dispatch(plants_df, demand_mw, carbon_price, wind_avail_pct, solar_avail_pct):
    """
    Run merit order dispatch to meet demand
    Returns detailed results dictionary
    """
    
    # Step 1: Apply renewable availability
    plants = apply_renewable_availability(plants_df, wind_avail_pct, solar_avail_pct)
    
    # Step 2: Calculate SRMC for each plant
    plants['SRMC_EUR_MWh'] = plants.apply(
        lambda row: calculate_srmc(row, carbon_price), 
        axis=1
    )
    
    # Step 3: Sort by SRMC (merit order)
    plants_sorted = plants.sort_values('SRMC_EUR_MWh').reset_index(drop=True)
    
    # Step 4: Dispatch plants to meet demand
    cumulative_capacity = 0
    dispatched_capacity = []
    dispatched_plants = []
    market_price = 0
    marginal_plant_idx = None
    
    for idx, plant in plants_sorted.iterrows():
        available_cap = plant['Available_Capacity_MW']
        
        if cumulative_capacity >= demand_mw:
            dispatched_capacity.append(0)
            dispatched_plants.append(False)
        elif cumulative_capacity + available_cap <= demand_mw:
            dispatched_capacity.append(available_cap)
            dispatched_plants.append(True)
            cumulative_capacity += available_cap
            market_price = plant['SRMC_EUR_MWh']
            marginal_plant_idx = idx
        else:
            remaining_demand = demand_mw - cumulative_capacity
            dispatched_capacity.append(remaining_demand)
            dispatched_plants.append(True)
            cumulative_capacity += remaining_demand
            market_price = plant['SRMC_EUR_MWh']
            marginal_plant_idx = idx
    
    # Add dispatch info to dataframe
    plants_sorted['Dispatched_Capacity_MW'] = dispatched_capacity
    plants_sorted['Is_Dispatched'] = dispatched_plants
    
    # Step 5: Calculate generation mix
    generation_by_technology = plants_sorted[plants_sorted['Is_Dispatched']].groupby('Technology')['Dispatched_Capacity_MW'].sum()
    generation_by_plant_type = plants_sorted[plants_sorted['Is_Dispatched']].groupby('Plant_Type')['Dispatched_Capacity_MW'].sum()
    
    # Step 6: Calculate emissions
    plants_sorted['Emissions_tons'] = plants_sorted['Dispatched_Capacity_MW'] * plants_sorted['CO2_Emissions_t_MWh']
    total_emissions = plants_sorted['Emissions_tons'].sum()
    
    # Step 7: Calculate costs
    plants_sorted['Generation_Cost_EUR'] = plants_sorted['Dispatched_Capacity_MW'] * plants_sorted['SRMC_EUR_MWh']
    total_generation_cost = plants_sorted['Generation_Cost_EUR'].sum()
    
    # Step 8: Calculate revenues and profits
    plants_sorted['Revenue_EUR'] = plants_sorted['Dispatched_Capacity_MW'] * market_price
    plants_sorted['Profit_EUR'] = plants_sorted['Revenue_EUR'] - plants_sorted['Generation_Cost_EUR']
    
    total_revenue = plants_sorted['Revenue_EUR'].sum()
    total_profit = plants_sorted['Profit_EUR'].sum()
    
    # Average emissions intensity
    avg_emissions_intensity = total_emissions / demand_mw if demand_mw > 0 else 0
    
    # Check if demand is met
    demand_met = cumulative_capacity >= demand_mw
    unmet_demand = max(0, demand_mw - cumulative_capacity)
    
    # Renewable share
    renewable_generation = generation_by_technology.get('Wind', 0) + generation_by_technology.get('Solar', 0) + generation_by_technology.get('Hydro', 0)
    renewable_share_pct = (renewable_generation / demand_mw * 100) if demand_mw > 0 else 0
    
    # ADVANCED METRICS (New additions inspired by Gemini)
    # Calculate potential renewable curtailment
    renewable_mask = plants_sorted['Technology'].isin(['Wind', 'Solar'])
    potential_renewable_mw = plants_sorted[renewable_mask]['Available_Capacity_MW'].sum()
    actual_renewable_mw = plants_sorted[renewable_mask]['Dispatched_Capacity_MW'].sum()
    renewable_curtailment_mw = potential_renewable_mw - actual_renewable_mw
    
    # Calculate system efficiency (price-to-cost ratio for marginal plant)
    if marginal_plant_idx is not None:
        marginal_plant_cost = plants_sorted.loc[marginal_plant_idx, 'SRMC_EUR_MWh']
        price_cost_ratio = market_price / marginal_plant_cost if marginal_plant_cost > 0 else 1.0
    else:
        price_cost_ratio = 1.0
    
    # Package results
    results = {
        'dispatch_df': plants_sorted,
        'market_price_eur_mwh': market_price,
        'marginal_plant_idx': marginal_plant_idx,
        'marginal_plant_name': plants_sorted.loc[marginal_plant_idx, 'Plant_Name'] if marginal_plant_idx is not None else 'None',
        'marginal_technology': plants_sorted.loc[marginal_plant_idx, 'Technology'] if marginal_plant_idx is not None else 'None',
        'total_generation_mw': cumulative_capacity,
        'demand_mw': demand_mw,
        'demand_met': demand_met,
        'unmet_demand_mw': unmet_demand,
        'total_emissions_tons': total_emissions,
        'avg_emissions_intensity_t_mwh': avg_emissions_intensity,
        'carbon_intensity_g_kwh': avg_emissions_intensity * 1000,  # Convert to g/kWh
        'total_generation_cost_eur': total_generation_cost,
        'total_revenue_eur': total_revenue,
        'total_profit_eur': total_profit,
        'generation_by_technology': generation_by_technology.to_dict(),
        'generation_by_plant_type': generation_by_plant_type.to_dict(),
        'renewable_share_pct': renewable_share_pct,
        'renewable_curtailment_mw': renewable_curtailment_mw,
        'carbon_price_eur_ton': carbon_price,
        'wind_availability_pct': wind_avail_pct,
        'solar_availability_pct': solar_avail_pct,
        'price_cost_ratio': price_cost_ratio
    }
    
    return results


def print_dispatch_summary(results, scenario_name=""):
    """Print formatted dispatch results"""
    print("\n" + "="*70)
    print(f"📊 DISPATCH RESULTS{' - ' + scenario_name if scenario_name else ''}")
    print("="*70)
    
    print(f"\n⚡ MARKET OVERVIEW:")
    print(f"   Market Price: €{results['market_price_eur_mwh']:.2f}/MWh")
    print(f"   Marginal Plant: {results['marginal_plant_name']} ({results['marginal_technology']})")
    print(f"   Demand: {results['demand_mw']:,.0f} MW")
    print(f"   Generation: {results['total_generation_mw']:,.0f} MW")
    print(f"   Demand Met: {'✅ YES' if results['demand_met'] else '❌ NO'}")
    if results['unmet_demand_mw'] > 0:
        print(f"   Unmet Demand: {results['unmet_demand_mw']:,.0f} MW")
    
    print(f"\n🌍 EMISSIONS:")
    print(f"   Total CO₂: {results['total_emissions_tons']:,.0f} tons")
    print(f"   Emissions Intensity: {results['avg_emissions_intensity_t_mwh']:.3f} t/MWh")
    print(f"   Carbon Intensity: {results['carbon_intensity_g_kwh']:.1f} g/kWh")
    
    print(f"\n💰 ECONOMICS:")
    print(f"   Total Generation Cost: €{results['total_generation_cost_eur']:,.0f}")
    print(f"   Total Revenue: €{results['total_revenue_eur']:,.0f}")
    print(f"   Total Profit (Producer Surplus): €{results['total_profit_eur']:,.0f}")
    
    print(f"\n🔋 GENERATION MIX:")
    gen_by_tech = results['generation_by_technology']
    total_gen = results['total_generation_mw']
    for tech, generation in sorted(gen_by_tech.items(), key=lambda x: x[1], reverse=True):
        pct = (generation / total_gen * 100) if total_gen > 0 else 0
        print(f"   {tech:15s}: {generation:8,.0f} MW ({pct:5.1f}%)")
    
    print(f"\n♻️  RENEWABLES:")
    print(f"   Renewable Share: {results['renewable_share_pct']:.1f}%")
    if results['renewable_curtailment_mw'] > 0:
        print(f"   Curtailment: {results['renewable_curtailment_mw']:,.0f} MW")
    
    print("\n" + "="*70)


# ===== SCENARIO RUNNER =====

def run_single_scenario(plants_df, scenario_row):
    """Run dispatch for a single scenario"""
    scenario_name = scenario_row['Scenario_Name']
    
    dispatch_results = run_merit_order_dispatch(
        plants_df=plants_df,
        demand_mw=scenario_row['Demand_MW'],
        carbon_price=scenario_row['Carbon_Price_EUR_ton'],
        wind_avail_pct=scenario_row['Wind_Availability_Percent'],
        solar_avail_pct=scenario_row['Solar_Availability_Percent']
    )
    
    # Add scenario metadata
    dispatch_results['scenario_name'] = scenario_name
    dispatch_results['period_type'] = scenario_row['Period_Type']
    dispatch_results['season'] = scenario_row['Season']
    
    return dispatch_results


def run_all_scenarios(plants_df, scenarios_df):
    """Run merit order dispatch for all scenarios"""
    print("\n" + "="*70)
    print("🚀 RUNNING ALL SCENARIOS")
    print("="*70)
    
    all_results = []
    
    for idx, scenario in scenarios_df.iterrows():
        scenario_name = scenario['Scenario_Name']
        print(f"\n⚙️  Running Scenario {idx+1}/{len(scenarios_df)}: {scenario_name}")
        
        results = run_single_scenario(plants_df, scenario)
        all_results.append(results)
        
        print(f"   ✅ Market Price: €{results['market_price_eur_mwh']:.2f}/MWh")
        print(f"   ✅ Emissions: {results['total_emissions_tons']:,.0f} tons CO₂")
        print(f"   ✅ Renewable Share: {results['renewable_share_pct']:.1f}%")
        print(f"   ✅ Demand Met: {'Yes' if results['demand_met'] else 'NO - SHORTAGE!'}")
    
    print("\n" + "="*70)
    print(f"✅ ALL {len(all_results)} SCENARIOS COMPLETED!")
    print("="*70)
    
    return all_results


def create_summary_dataframe(all_results):
    """Create summary DataFrame from all scenario results"""
    summary_data = []
    
    for result in all_results:
        row = {
            'Scenario_Name': result['scenario_name'],
            'Period_Type': result['period_type'],
            'Season': result['season'],
            'Demand_MW': result['demand_mw'],
            'Carbon_Price_EUR_ton': result['carbon_price_eur_ton'],
            'Wind_Avail_%': result['wind_availability_pct'],
            'Solar_Avail_%': result['solar_availability_pct'],
            'Market_Price_EUR_MWh': result['market_price_eur_mwh'],
            'Marginal_Technology': result['marginal_technology'],
            'Total_Generation_MW': result['total_generation_mw'],
            'Demand_Met': result['demand_met'],
            'Unmet_Demand_MW': result['unmet_demand_mw'],
            'Total_Emissions_tons': result['total_emissions_tons'],
            'Emissions_Intensity_t_MWh': result['avg_emissions_intensity_t_mwh'],
            'Carbon_Intensity_g_kWh': result['carbon_intensity_g_kwh'],
            'Renewable_Share_%': result['renewable_share_pct'],
            'Renewable_Curtailment_MW': result['renewable_curtailment_mw'],
            'Total_Cost_EUR': result['total_generation_cost_eur'],
            'Total_Revenue_EUR': result['total_revenue_eur'],
            'Producer_Surplus_EUR': result['total_profit_eur'],
            'Marginal_Plant': result['marginal_plant_name']
        }
        
        # Add generation by technology
        gen_by_tech = result['generation_by_technology']
        for tech, gen_mw in gen_by_tech.items():
            row[f'Gen_{tech}_MW'] = gen_mw
        
        summary_data.append(row)
    
    summary_df = pd.DataFrame(summary_data)
    return summary_df


def display_comparison_table(summary_df):
    """Display key metrics comparison across scenarios"""
    print("\n" + "="*70)
    print("📊 SCENARIO COMPARISON TABLE")
    print("="*70)
    
    display_cols = [
        'Scenario_Name',
        'Demand_MW',
        'Market_Price_EUR_MWh',
        'Total_Emissions_tons',
        'Renewable_Share_%',
        'Demand_Met'
    ]
    
    display_df = summary_df[display_cols].copy()
    
    # Format numbers
    display_df['Demand_MW'] = display_df['Demand_MW'].apply(lambda x: f"{x:,.0f}")
    display_df['Market_Price_EUR_MWh'] = display_df['Market_Price_EUR_MWh'].apply(lambda x: f"€{x:.2f}")
    display_df['Total_Emissions_tons'] = display_df['Total_Emissions_tons'].apply(lambda x: f"{x:,.0f}")
    display_df['Renewable_Share_%'] = display_df['Renewable_Share_%'].apply(lambda x: f"{x:.1f}%")
    display_df['Demand_Met'] = display_df['Demand_Met'].apply(lambda x: '✅' if x else '❌')
    
    print(display_df.to_string(index=False))
    print("\n" + "="*70)
    
    # Print insights
    print("\n📈 KEY INSIGHTS:")
    
    # Price range
    min_price = summary_df['Market_Price_EUR_MWh'].min()
    max_price = summary_df['Market_Price_EUR_MWh'].max()
    min_price_scenario = summary_df.loc[summary_df['Market_Price_EUR_MWh'].idxmin(), 'Scenario_Name']
    max_price_scenario = summary_df.loc[summary_df['Market_Price_EUR_MWh'].idxmax(), 'Scenario_Name']
    
    print(f"   💰 Price Range: €{min_price:.2f} - €{max_price:.2f}/MWh")
    print(f"      Lowest: {min_price_scenario} (€{min_price:.2f})")
    print(f"      Highest: {max_price_scenario} (€{max_price:.2f})")
    
    # Emissions
    min_emissions = summary_df['Total_Emissions_tons'].min()
    max_emissions = summary_df['Total_Emissions_tons'].max()
    
    print(f"\n   🌍 Emissions Range: {min_emissions:,.0f} - {max_emissions:,.0f} tons CO₂")
    
    # Renewable share
    avg_renewable = summary_df['Renewable_Share_%'].mean()
    max_renewable = summary_df['Renewable_Share_%'].max()
    
    print(f"\n   ♻️  Average Renewable Share: {avg_renewable:.1f}%")
    print(f"      Maximum Renewable Share: {max_renewable:.1f}%")
    
    # Price setters (market dynamics)
    print(f"\n   👑 Price Setting Technologies:")
    price_setters = summary_df['Marginal_Technology'].value_counts()
    for tech, count in price_setters.items():
        pct = (count / len(summary_df)) * 100
        print(f"      {tech}: {count} times ({pct:.0f}%)")
    
    # Demand not met
    unmet_scenarios = summary_df[~summary_df['Demand_Met']]
    if len(unmet_scenarios) > 0:
        print(f"\n   ⚠️  WARNING: {len(unmet_scenarios)} scenario(s) with unmet demand:")
        for _, row in unmet_scenarios.iterrows():
            print(f"      - {row['Scenario_Name']}: {row['Unmet_Demand_MW']:,.0f} MW shortage")
    else:
        print(f"\n   ✅ All scenarios meet demand successfully!")
    
    print("\n" + "="*70)

# ===== SECTION 4: VISUALIZATION FUNCTIONS =====

def create_merit_order_curve(dispatch_df, demand_mw, market_price, scenario_name, save_path):
    """
    Create the classic merit order curve (supply curve staircase)
    Shows how plants stack up by cost
    """
    # Prepare data for step chart
    # We need cumulative capacity for x-axis
    dispatch_df = dispatch_df.copy()
    dispatch_df['Cumulative_Start'] = dispatch_df['Available_Capacity_MW'].cumsum().shift(1).fillna(0)
    dispatch_df['Cumulative_End'] = dispatch_df['Available_Capacity_MW'].cumsum()
    
    # Create figure
    plt.figure(figsize=(14, 8))
    
    # Plot merit order curve as steps
    for idx, row in dispatch_df.iterrows():
        color = 'green' if row['Is_Dispatched'] else 'lightgray'
        
        # Technology-based coloring for dispatched plants
        if row['Is_Dispatched']:
            if row['Technology'] == 'Wind':
                color = '#3498db'  # Blue
            elif row['Technology'] == 'Solar':
                color = '#f39c12'  # Orange
            elif row['Technology'] == 'Hydro':
                color = '#1abc9c'  # Teal
            elif row['Technology'] == 'Gas':
                color = '#e74c3c'  # Red
            elif row['Technology'] == 'Coal':
                color = '#34495e'  # Dark gray
            elif row['Technology'] == 'Gas Peaker':
                color = '#c0392b'  # Dark red
            elif row['Technology'] == 'Biomass':
                color = '#27ae60'  # Green
        
        # Draw horizontal line (the step)
        plt.hlines(
            y=row['SRMC_EUR_MWh'],
            xmin=row['Cumulative_Start'],
            xmax=row['Cumulative_End'],
            colors=color,
            linewidth=2,
            alpha=0.8
        )
        
        # Draw vertical line (connecting steps)
        if idx > 0:
            prev_price = dispatch_df.iloc[idx-1]['SRMC_EUR_MWh']
            plt.vlines(
                x=row['Cumulative_Start'],
                ymin=min(prev_price, row['SRMC_EUR_MWh']),
                ymax=max(prev_price, row['SRMC_EUR_MWh']),
                colors=color,
                linewidth=2,
                alpha=0.8
            )
    
    # Add demand line
    plt.axvline(x=demand_mw, color='red', linestyle='--', linewidth=2, label='Demand', alpha=0.7)
    
    # Add market price line
    plt.axhline(y=market_price, color='purple', linestyle='--', linewidth=2, 
                label=f'Market Price: €{market_price:.2f}/MWh', alpha=0.7)
    
    # Formatting
    plt.xlabel('Cumulative Capacity (MW)', fontsize=12, fontweight='bold')
    plt.ylabel('SRMC (€/MWh)', fontsize=12, fontweight='bold')
    plt.title(f'Merit Order Curve - {scenario_name}', fontsize=14, fontweight='bold', pad=20)
    plt.grid(True, alpha=0.3)
    plt.legend(loc='upper left', fontsize=10)
    
    # Add text box with key metrics
    textstr = f'Demand: {demand_mw:,.0f} MW\nMarket Price: €{market_price:.2f}/MWh'
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
    plt.text(0.98, 0.97, textstr, transform=plt.gca().transAxes, fontsize=10,
             verticalalignment='top', horizontalalignment='right', bbox=props)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"   ✅ Saved: {save_path}")


def create_generation_mix_pie(results, scenario_name, save_path):
    """
    Create pie chart showing generation mix by technology
    """
    gen_by_tech = results['generation_by_technology']
    
    # Prepare data
    technologies = list(gen_by_tech.keys())
    generation = list(gen_by_tech.values())
    
    # Define colors for each technology
    color_map = {
        'Wind': '#3498db',
        'Solar': '#f39c12',
        'Hydro': '#1abc9c',
        'Gas': '#e74c3c',
        'Coal': '#34495e',
        'Gas Peaker': '#c0392b',
        'Biomass': '#27ae60'
    }
    colors = [color_map.get(tech, '#95a5a6') for tech in technologies]
    
    # Create figure
    plt.figure(figsize=(10, 8))
    
    # Create pie chart
    wedges, texts, autotexts = plt.pie(
        generation,
        labels=technologies,
        autopct='%1.1f%%',
        colors=colors,
        startangle=90,
        textprops={'fontsize': 11, 'fontweight': 'bold'}
    )
    
    # Improve text visibility
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
    
    plt.title(f'Generation Mix by Technology - {scenario_name}', 
              fontsize=14, fontweight='bold', pad=20)
    
    # Add legend with generation values
    legend_labels = [f'{tech}: {gen:,.0f} MW' for tech, gen in zip(technologies, generation)]
    plt.legend(legend_labels, loc='center left', bbox_to_anchor=(1, 0, 0.5, 1), fontsize=10)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"   ✅ Saved: {save_path}")


def create_scenario_comparison_chart(summary_df, save_path):
    """
    Create bar chart comparing key metrics across all scenarios
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Scenario Comparison Dashboard', fontsize=16, fontweight='bold', y=0.995)
    
    scenarios = summary_df['Scenario_Name'].tolist()
    
    # 1. Market Prices
    ax1 = axes[0, 0]
    prices = summary_df['Market_Price_EUR_MWh'].tolist()
    bars1 = ax1.bar(range(len(scenarios)), prices, color='#3498db', alpha=0.8)
    ax1.set_xticks(range(len(scenarios)))
    ax1.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=9)
    ax1.set_ylabel('Market Price (€/MWh)', fontsize=11, fontweight='bold')
    ax1.set_title('Market Clearing Prices', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'€{height:.1f}', ha='center', va='bottom', fontsize=8)
    
    # 2. Emissions
    ax2 = axes[0, 1]
    emissions = summary_df['Total_Emissions_tons'].tolist()
    bars2 = ax2.bar(range(len(scenarios)), emissions, color='#e74c3c', alpha=0.8)
    ax2.set_xticks(range(len(scenarios)))
    ax2.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=9)
    ax2.set_ylabel('Total Emissions (tons CO₂)', fontsize=11, fontweight='bold')
    ax2.set_title('Carbon Emissions', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')
    
    # Add value labels
    for bar in bars2:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:,.0f}', ha='center', va='bottom', fontsize=8)
    
    # 3. Renewable Share
    ax3 = axes[1, 0]
    renewable_share = summary_df['Renewable_Share_%'].tolist()
    bars3 = ax3.bar(range(len(scenarios)), renewable_share, color='#27ae60', alpha=0.8)
    ax3.set_xticks(range(len(scenarios)))
    ax3.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=9)
    ax3.set_ylabel('Renewable Share (%)', fontsize=11, fontweight='bold')
    ax3.set_title('Renewable Energy Penetration', fontsize=12, fontweight='bold')
    ax3.axhline(y=50, color='red', linestyle='--', linewidth=1, alpha=0.5, label='50% Target')
    ax3.grid(True, alpha=0.3, axis='y')
    ax3.legend(fontsize=9)
    
    # Add value labels
    for bar in bars3:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%', ha='center', va='bottom', fontsize=8)
    
    # 4. Producer Surplus (Profit)
    ax4 = axes[1, 1]
    profit = summary_df['Producer_Surplus_EUR'].tolist()
    bars4 = ax4.bar(range(len(scenarios)), profit, color='#f39c12', alpha=0.8)
    ax4.set_xticks(range(len(scenarios)))
    ax4.set_xticklabels(scenarios, rotation=45, ha='right', fontsize=9)
    ax4.set_ylabel('Producer Surplus (€)', fontsize=11, fontweight='bold')
    ax4.set_title('Economic Profit (Producer Surplus)', fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y')
    
    # Add value labels
    for bar in bars4:
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                f'€{height:,.0f}', ha='center', va='bottom', fontsize=7)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"   ✅ Saved: {save_path}")


def create_carbon_price_sensitivity(summary_df, save_path):
    """
    Create scatter plot showing relationship between carbon price and market price
    """
    plt.figure(figsize=(12, 8))
    
    # Extract data
    carbon_prices = summary_df['Carbon_Price_EUR_ton'].tolist()
    market_prices = summary_df['Market_Price_EUR_MWh'].tolist()
    scenarios = summary_df['Scenario_Name'].tolist()
    renewable_share = summary_df['Renewable_Share_%'].tolist()
    
    # Create scatter plot with color-coding by renewable share
    scatter = plt.scatter(carbon_prices, market_prices, 
                         c=renewable_share, 
                         s=200, 
                         alpha=0.6,
                         cmap='RdYlGn',
                         edgecolors='black',
                         linewidth=1.5)
    
    # Add labels for each point
    for i, scenario in enumerate(scenarios):
        plt.annotate(scenario, 
                    (carbon_prices[i], market_prices[i]),
                    textcoords="offset points",
                    xytext=(0, 10),
                    ha='center',
                    fontsize=8,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.3))
    
    # Add colorbar
    cbar = plt.colorbar(scatter)
    cbar.set_label('Renewable Share (%)', rotation=270, labelpad=20, fontsize=11, fontweight='bold')
    
    # Add trend line
    if len(carbon_prices) > 1:
        z = np.polyfit(carbon_prices, market_prices, 1)
        p = np.poly1d(z)
        plt.plot(carbon_prices, p(carbon_prices), "r--", alpha=0.8, linewidth=2, label='Trend Line')
    
    # Formatting
    plt.xlabel('Carbon Price (€/ton CO₂)', fontsize=12, fontweight='bold')
    plt.ylabel('Market Clearing Price (€/MWh)', fontsize=12, fontweight='bold')
    plt.title('Carbon Price vs Market Price Sensitivity Analysis', fontsize=14, fontweight='bold', pad=20)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=10)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"   ✅ Saved: {save_path}")


def create_emissions_intensity_chart(summary_df, save_path):
    """
    Create bar chart showing emissions intensity with EU target comparison
    """
    plt.figure(figsize=(14, 8))
    
    scenarios = summary_df['Scenario_Name'].tolist()
    emissions_intensity = summary_df['Carbon_Intensity_g_kWh'].tolist()
    
    # Create bars with color gradient based on intensity
    colors = ['#27ae60' if x < 100 else '#f39c12' if x < 300 else '#e74c3c' for x in emissions_intensity]
    
    bars = plt.bar(range(len(scenarios)), emissions_intensity, color=colors, alpha=0.8, edgecolor='black')
    
    # Add EU 2030 target line (example: 100 g/kWh)
    plt.axhline(y=100, color='green', linestyle='--', linewidth=2, label='EU 2030 Target (~100 g/kWh)', alpha=0.7)
    
    # Add value labels
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}', ha='center', va='bottom', fontsize=9, fontweight='bold')
    
    plt.xticks(range(len(scenarios)), scenarios, rotation=45, ha='right', fontsize=10)
    plt.ylabel('Carbon Intensity (g CO₂/kWh)', fontsize=12, fontweight='bold')
    plt.title('Emissions Intensity by Scenario (EU Climate Target Comparison)', fontsize=14, fontweight='bold', pad=20)
    plt.grid(True, alpha=0.3, axis='y')
    plt.legend(fontsize=11, loc='upper left')
    
    # Add color legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#27ae60', alpha=0.8, label='Below Target (<100 g/kWh)'),
        Patch(facecolor='#f39c12', alpha=0.8, label='Moderate (100-300 g/kWh)'),
        Patch(facecolor='#e74c3c', alpha=0.8, label='High (>300 g/kWh)')
    ]
    plt.legend(handles=legend_elements, loc='upper right', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"   ✅ Saved: {save_path}")


def create_technology_stack_chart(summary_df, save_path):
    """
    Create stacked area chart showing generation mix evolution across scenarios
    """
    # Extract generation data by technology
    tech_columns = [col for col in summary_df.columns if col.startswith('Gen_') and col.endswith('_MW')]
    technologies = [col.replace('Gen_', '').replace('_MW', '') for col in tech_columns]
    
    # Prepare data matrix
    data_matrix = []
    for tech_col in tech_columns:
        if tech_col in summary_df.columns:
            data_matrix.append(summary_df[tech_col].fillna(0).tolist())
        else:
            data_matrix.append([0] * len(summary_df))
    
    scenarios = summary_df['Scenario_Name'].tolist()
    x_pos = range(len(scenarios))
    
    # Create figure
    plt.figure(figsize=(16, 8))
    
    # Color mapping
    color_map = {
        'Wind': '#3498db',
        'Solar': '#f39c12',
        'Hydro': '#1abc9c',
        'Gas': '#e74c3c',
        'Coal': '#34495e',
        'Gas Peaker': '#c0392b',
        'Biomass': '#27ae60'
    }
    
    colors = [color_map.get(tech, '#95a5a6') for tech in technologies]
    
    # Create stacked bar chart
    bottom = np.zeros(len(scenarios))
    
    for i, (tech, data) in enumerate(zip(technologies, data_matrix)):
        plt.bar(x_pos, data, bottom=bottom, label=tech, color=colors[i], alpha=0.8, edgecolor='white')
        bottom += np.array(data)
    
    # Formatting
    plt.xticks(x_pos, scenarios, rotation=45, ha='right', fontsize=10)
    plt.ylabel('Generation (MW)', fontsize=12, fontweight='bold')
    plt.title('Generation Mix Technology Stack Across Scenarios', fontsize=14, fontweight='bold', pad=20)
    plt.legend(loc='upper left', bbox_to_anchor=(1, 1), fontsize=11)
    plt.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"   ✅ Saved: {save_path}")


def create_all_visualizations(all_results, summary_df, plants_df):
    """
    Master function to create all visualizations
    """
    print("\n" + "="*70)
    print("🎨 CREATING VISUALIZATIONS")
    print("="*70)
    
    # Create subdirectory for charts
    charts_dir = CHARTS_DIR
    
    # 1. Merit Order Curves for selected scenarios
    print("\n📊 Creating Merit Order Curves...")
    selected_scenarios = ['Base_Load_Summer', 'Peak_Load_Winter', 'Extreme_Peak', 'High_Wind_Day']
    
    for scenario_name in selected_scenarios:
        result = next((r for r in all_results if r['scenario_name'] == scenario_name), None)
        if result:
            save_path = os.path.join(charts_dir, f'merit_order_{scenario_name}.png')
            create_merit_order_curve(
                result['dispatch_df'],
                result['demand_mw'],
                result['market_price_eur_mwh'],
                scenario_name,
                save_path
            )
    
    # 2. Generation Mix Pie Charts
    print("\n🥧 Creating Generation Mix Charts...")
    for scenario_name in selected_scenarios:
        result = next((r for r in all_results if r['scenario_name'] == scenario_name), None)
        if result:
            save_path = os.path.join(charts_dir, f'generation_mix_{scenario_name}.png')
            create_generation_mix_pie(result, scenario_name, save_path)
    
    # 3. Scenario Comparison Dashboard
    print("\n📊 Creating Scenario Comparison Dashboard...")
    save_path = os.path.join(charts_dir, 'scenario_comparison_dashboard.png')
    create_scenario_comparison_chart(summary_df, save_path)
    
    # 4. Carbon Price Sensitivity
    print("\n💰 Creating Carbon Price Sensitivity Analysis...")
    save_path = os.path.join(charts_dir, 'carbon_price_sensitivity.png')
    create_carbon_price_sensitivity(summary_df, save_path)
    
    # 5. Emissions Intensity
    print("\n🌍 Creating Emissions Intensity Chart...")
    save_path = os.path.join(charts_dir, 'emissions_intensity_comparison.png')
    create_emissions_intensity_chart(summary_df, save_path)
    
    # 6. Technology Stack
    print("\n📊 Creating Technology Stack Chart...")
    save_path = os.path.join(charts_dir, 'technology_stack.png')
    create_technology_stack_chart(summary_df, save_path)
    
    print("\n" + "="*70)
    print(f"✅ ALL VISUALIZATIONS CREATED!")
    print(f"📁 Saved to: {charts_dir}")
    print("="*70)

# ===== MAIN EXECUTION =====

if __name__ == "__main__":
    print("\n🧪 STARTING ANALYSIS...")
    print("-"*70)
    
    # Load data
    plants = load_plant_database()
    scenarios = load_scenarios()
    
    if plants is not None and scenarios is not None:
        print("✅ ALL DATA LOADED SUCCESSFULLY!")
        print()
        
        # Display summary
        display_data_summary(plants, scenarios)
        
        # Test single scenario
        print("\n🧪 TESTING SINGLE SCENARIO DISPATCH...")
        print("-"*70)
        
        test_scenario = scenarios[scenarios['Scenario_Name'] == 'Base_Load_Summer'].iloc[0]
        
        print(f"\n📋 Testing Scenario: {test_scenario['Scenario_Name']}")
        results = run_merit_order_dispatch(
            plants_df=plants,
            demand_mw=test_scenario['Demand_MW'],
            carbon_price=test_scenario['Carbon_Price_EUR_ton'],
            wind_avail_pct=test_scenario['Wind_Availability_Percent'],
            solar_avail_pct=test_scenario['Solar_Availability_Percent']
        )
        
        print_dispatch_summary(results, test_scenario['Scenario_Name'])
        
        print("\n✅ Single scenario test complete!")
        
        # Run all scenarios
        all_results = run_all_scenarios(plants, scenarios)
        
        # Create summary
        summary_df = create_summary_dataframe(all_results)
        
        # Display comparison
        display_comparison_table(summary_df)
        
        # Save CSV results
        print("\n💾 Saving CSV results...")
        summary_df.to_csv(os.path.join(OUTPUT_DIR, 'scenario_summary.csv'), index=False)
        print(f"   ✅ Saved to: {os.path.join(OUTPUT_DIR, 'scenario_summary.csv')}")
        
        # CREATE ALL VISUALIZATIONS
        create_all_visualizations(all_results, summary_df, plants)
        
        print("\n🎉 ANALYSIS COMPLETE!")
        print("="*70)
        print("\n📊 DELIVERABLES:")
        print(f"   📄 CSV Summary: {os.path.join(OUTPUT_DIR, 'scenario_summary.csv')}")
        print(f"   📊 Charts: {CHARTS_DIR}")
        print("\n🚀 Next Step: Build Streamlit Web App (Section 5)")
        print("="*70)
        
    else:
        print("❌ DATA LOADING FAILED!")