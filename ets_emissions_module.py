# =====================================================================
# EU ETS EMISSIONS MODULE - MODULAR ADDITIONS
# To be added to power_market_analyzer_fixed.py
# Author: Felix Okumo
# Date: January 2026
# Description: EU ETS switching price calculation and BI-ready exports
# =====================================================================

import pandas as pd
import numpy as np

# ===== SECTION 1: EMISSIONS SWITCHING PRICE CALCULATION =====

def calculate_switching_price(plants_df, coal_efficiency=0.38, gas_efficiency=0.55,
                              coal_emission_factor=0.34, gas_emission_factor=0.20):
    """
    Calculate Coal-to-Gas Switching Price based on EU ETS dynamics
    
    This is the carbon price at which gas becomes cheaper than coal for electricity generation,
    accounting for differences in fuel costs, efficiencies, and emission factors.
    
    Formula:
    Switching Price = (Gas Fuel Cost/Gas Eff - Coal Fuel Cost/Coal Eff) / 
                     (Coal Emission/Coal Eff - Gas Emission/Gas Eff)
    
    Parameters:
    -----------
    plants_df : DataFrame
        Power plant database with columns: Technology, Fuel_Cost_EUR_MWh
    coal_efficiency : float
        Coal plant thermal efficiency (default: 0.38 = 38%)
    gas_efficiency : float
        Gas plant thermal efficiency (default: 0.55 = 55%)
    coal_emission_factor : float
        Coal CO2 emission factor in tCO2/MWh_thermal (default: 0.34)
    gas_emission_factor : float
        Gas CO2 emission factor in tCO2/MWh_thermal (default: 0.20)
    
    Returns:
    --------
    dict : Dictionary containing:
        - switching_price_eur_ton: The calculated switching price
        - coal_fuel_cost: Average coal fuel cost
        - gas_fuel_cost: Average gas fuel cost
        - coal_marginal_cost: Coal generation cost at switching point
        - gas_marginal_cost: Gas generation cost at switching point
    """
    
    # Extract fuel costs
    coal_plants = plants_df[plants_df['Technology'] == 'Coal']
    gas_plants = plants_df[plants_df['Technology'].isin(['Gas', 'Gas Peaker'])]
    
    # Calculate average fuel costs
    if len(coal_plants) == 0:
        raise ValueError("No coal plants found in database")
    if len(gas_plants) == 0:
        raise ValueError("No gas plants found in database")
    
    coal_fuel_cost = coal_plants['Fuel_Cost_EUR_MWh'].mean()
    gas_fuel_cost = gas_plants['Fuel_Cost_EUR_MWh'].mean()
    
    # Calculate generation costs per MWh (fuel cost / efficiency)
    coal_gen_cost = coal_fuel_cost / coal_efficiency  # €/MWh_electric
    gas_gen_cost = gas_fuel_cost / gas_efficiency     # €/MWh_electric
    
    # Calculate emission rates per MWh_electric
    coal_emission_rate = coal_emission_factor / coal_efficiency  # tCO2/MWh_electric
    gas_emission_rate = gas_emission_factor / gas_efficiency    # tCO2/MWh_electric
    
    # Switching price formula
    # At switching price: Coal_SRMC = Gas_SRMC
    # Coal_Fuel/Eff + Carbon*Coal_Emission/Eff = Gas_Fuel/Eff + Carbon*Gas_Emission/Eff
    # Solving for Carbon price:
    numerator = gas_gen_cost - coal_gen_cost
    denominator = coal_emission_rate - gas_emission_rate
    
    if denominator <= 0:
        raise ValueError("Invalid emission factors: Gas must have lower emissions than coal")
    
    switching_price = numerator / denominator
    
    # Calculate costs at switching point
    coal_cost_at_switch = coal_gen_cost + (switching_price * coal_emission_rate)
    gas_cost_at_switch = gas_gen_cost + (switching_price * gas_emission_rate)
    
    return {
        'switching_price_eur_ton': switching_price,
        'coal_fuel_cost_eur_mwh': coal_fuel_cost,
        'gas_fuel_cost_eur_mwh': gas_fuel_cost,
        'coal_generation_cost_eur_mwh': coal_gen_cost,
        'gas_generation_cost_eur_mwh': gas_gen_cost,
        'coal_emission_rate_t_mwh': coal_emission_rate,
        'gas_emission_rate_t_mwh': gas_emission_rate,
        'coal_srmc_at_switching_eur_mwh': coal_cost_at_switch,
        'gas_srmc_at_switching_eur_mwh': gas_cost_at_switch,
        'formula_validation': abs(coal_cost_at_switch - gas_cost_at_switch) < 0.01  # Should be ~equal
    }


def interpret_switching_price(current_carbon_price, switching_price_data):
    """
    Interpret the switching price result and provide market insights
    
    Parameters:
    -----------
    current_carbon_price : float
        Current EU ETS carbon price (€/ton)
    switching_price_data : dict
        Output from calculate_switching_price()
    
    Returns:
    --------
    dict : Market interpretation with key insights
    """
    switching_price = switching_price_data['switching_price_eur_ton']
    
    # Determine market regime
    if current_carbon_price < switching_price:
        regime = "COAL-DOMINATED"
        marginal_tech = "Coal"
        explanation = "Carbon price is below switching point. Coal plants are more economical than gas."
    elif current_carbon_price > switching_price:
        regime = "GAS-DOMINATED"
        marginal_tech = "Gas"
        explanation = "Carbon price is above switching point. Gas plants are more economical than coal."
    else:
        regime = "TRANSITION ZONE"
        marginal_tech = "Coal/Gas (Indifferent)"
        explanation = "Carbon price is at switching point. Coal and gas have equal generation costs."
    
    # Calculate how far from switching point
    price_difference = current_carbon_price - switching_price
    percentage_difference = (price_difference / switching_price) * 100
    
    return {
        'market_regime': regime,
        'marginal_technology': marginal_tech,
        'explanation': explanation,
        'carbon_price_vs_switching': price_difference,
        'percentage_above_below_switching': percentage_difference,
        'switching_price': switching_price,
        'current_carbon_price': current_carbon_price,
        'is_coal_cheaper': current_carbon_price < switching_price,
        'is_gas_cheaper': current_carbon_price > switching_price
    }


# ===== SECTION 2: BI-READY DATA EXPORT =====

def prepare_bi_export(summary_df):
    """
    Transform wide-format scenario summary into long-format for Power BI / Tableau
    
    Converts from:
        Scenario_Name | Market_Price | Emissions | Renewable_Share | ...
        Scenario_1    | 50.2        | 1000      | 45.3           | ...
        Scenario_2    | 62.1        | 800       | 52.1           | ...
    
    To:
        Scenario_Name | Season | Period_Type | KPI_Metric      | Value
        Scenario_1    | Summer | Base_Load   | Market_Price    | 50.2
        Scenario_1    | Summer | Base_Load   | Emissions       | 1000
        Scenario_2    | Winter | Peak_Load   | Market_Price    | 62.1
        ...
    
    Parameters:
    -----------
    summary_df : DataFrame
        Wide-format summary with scenarios as rows and metrics as columns
    
    Returns:
    --------
    DataFrame : Long-format data optimized for BI tools
    """
    
    # Make a copy to avoid modifying original
    df = summary_df.copy()
    
    # Define identifier columns (will be preserved during melt)
    id_columns = ['Scenario_Name']
    
    # Add optional identifier columns if they exist
    optional_ids = ['Period_Type', 'Season', 'Demand_MW', 'Carbon_Price_EUR_ton', 
                   'Wind_Avail_%', 'Solar_Avail_%']
    
    for col in optional_ids:
        if col in df.columns:
            id_columns.append(col)
    
    # Define value columns (metrics to melt)
    # These are all columns except the identifiers
    value_columns = [col for col in df.columns if col not in id_columns]
    
    # Melt the dataframe
    bi_ready_df = pd.melt(
        df,
        id_vars=id_columns,
        value_vars=value_columns,
        var_name='KPI_Metric',
        value_name='Value'
    )
    
    # Add metadata columns for better BI filtering
    bi_ready_df['Data_Type'] = bi_ready_df['KPI_Metric'].apply(classify_metric_type)
    bi_ready_df['Unit'] = bi_ready_df['KPI_Metric'].apply(get_metric_unit)
    
    # Sort for better readability
    bi_ready_df = bi_ready_df.sort_values(['Scenario_Name', 'KPI_Metric']).reset_index(drop=True)
    
    return bi_ready_df


def classify_metric_type(metric_name):
    """
    Classify KPI metrics into categories for BI filtering
    
    Parameters:
    -----------
    metric_name : str
        Name of the KPI metric
    
    Returns:
    --------
    str : Category (Economic, Environmental, Technical, or Other)
    """
    economic_keywords = ['Price', 'Cost', 'Revenue', 'Surplus', 'EUR']
    environmental_keywords = ['Emissions', 'Carbon', 'Intensity', 'CO2', 'Renewable']
    technical_keywords = ['Generation', 'Demand', 'Capacity', 'MW', 'Curtailment', 'Avail']
    
    metric_lower = metric_name.lower()
    
    if any(keyword.lower() in metric_lower for keyword in economic_keywords):
        return 'Economic'
    elif any(keyword.lower() in metric_lower for keyword in environmental_keywords):
        return 'Environmental'
    elif any(keyword.lower() in metric_lower for keyword in technical_keywords):
        return 'Technical'
    else:
        return 'Other'


def get_metric_unit(metric_name):
    """
    Infer the unit of measurement from metric name
    
    Parameters:
    -----------
    metric_name : str
        Name of the KPI metric
    
    Returns:
    --------
    str : Unit of measurement
    """
    metric_lower = metric_name.lower()
    
    # Define unit mappings
    unit_mappings = {
        'eur': '€',
        'price': '€/MWh',
        'cost': '€',
        'revenue': '€',
        'surplus': '€',
        'mw': 'MW',
        'demand': 'MW',
        'generation': 'MW',
        'capacity': 'MW',
        'emissions': 'tons CO₂',
        'intensity': 't/MWh or g/kWh',
        'share': '%',
        'avail': '%',
        'curtailment': 'MW',
        'carbon_price': '€/ton'
    }
    
    # Check for matches
    for keyword, unit in unit_mappings.items():
        if keyword in metric_lower:
            return unit
    
    return '-'  # No unit identified


# ===== SECTION 3: ENHANCED SCENARIO ANALYSIS =====

def add_switching_analysis_to_summary(summary_df, plants_df):
    """
    Add switching price analysis columns to scenario summary
    
    Parameters:
    -----------
    summary_df : DataFrame
        Existing scenario summary
    plants_df : DataFrame
        Power plant database
    
    Returns:
    --------
    DataFrame : Summary with additional switching price columns
    """
    
    # Calculate switching price once (same for all scenarios)
    try:
        switching_data = calculate_switching_price(plants_df)
        switching_price = switching_data['switching_price_eur_ton']
    except Exception as e:
        print(f"⚠️  Warning: Could not calculate switching price - {str(e)}")
        return summary_df
    
    # Add switching price column
    summary_df['Switching_Price_EUR_ton'] = switching_price
    
    # Add market regime column
    summary_df['Market_Regime'] = summary_df['Carbon_Price_EUR_ton'].apply(
        lambda cp: 'COAL-DOMINATED' if cp < switching_price 
        else 'GAS-DOMINATED' if cp > switching_price 
        else 'TRANSITION'
    )
    
    # Add distance from switching point
    summary_df['Carbon_Price_vs_Switching_EUR'] = (
        summary_df['Carbon_Price_EUR_ton'] - switching_price
    )
    
    # Add percentage difference
    summary_df['Carbon_Price_vs_Switching_%'] = (
        (summary_df['Carbon_Price_vs_Switching_EUR'] / switching_price) * 100
    )
    
    return summary_df


# ===== SECTION 4: VALIDATION & TESTING =====

def validate_switching_price_calculation():
    """
    Test the switching price calculation with known values
    
    This is a self-contained validation function
    """
    print("\n" + "="*70)
    print("🧪 VALIDATING SWITCHING PRICE CALCULATION")
    print("="*70)
    
    # Create test data
    test_plants = pd.DataFrame({
        'Plant_Name': ['Coal_Test', 'Gas_Test'],
        'Technology': ['Coal', 'Gas'],
        'Fuel_Cost_EUR_MWh': [25.0, 45.0],  # Typical values
        'Capacity_MW': [500, 500]
    })
    
    # Calculate switching price
    result = calculate_switching_price(test_plants)
    
    print(f"\n📊 Test Results:")
    print(f"   Switching Price: €{result['switching_price_eur_ton']:.2f}/ton")
    print(f"   Coal Fuel Cost: €{result['coal_fuel_cost_eur_mwh']:.2f}/MWh")
    print(f"   Gas Fuel Cost: €{result['gas_fuel_cost_eur_mwh']:.2f}/MWh")
    print(f"   Coal SRMC at Switch: €{result['coal_srmc_at_switching_eur_mwh']:.2f}/MWh")
    print(f"   Gas SRMC at Switch: €{result['gas_srmc_at_switching_eur_mwh']:.2f}/MWh")
    print(f"   Formula Validated: {'✅ YES' if result['formula_validation'] else '❌ NO'}")
    
    # Expected range check
    if 30 <= result['switching_price_eur_ton'] <= 80:
        print(f"\n✅ Switching price is in expected range (€30-80/ton)")
    else:
        print(f"\n⚠️  Warning: Switching price outside typical range")
    
    # Test interpretation
    test_carbon_prices = [30, 50, 70]
    print(f"\n📈 Market Regime Analysis:")
    for cp in test_carbon_prices:
        interpretation = interpret_switching_price(cp, result)
        print(f"   Carbon Price €{cp}/ton → {interpretation['market_regime']}")
    
    print("\n" + "="*70)
    print("✅ VALIDATION COMPLETE")
    print("="*70)
    
    return result


# ===== USAGE EXAMPLES =====

if __name__ == "__main__":
    """
    Example usage - this will only run if the file is executed directly,
    not when imported as a module
    """
    
    print("\n📚 EU ETS EMISSIONS MODULE - USAGE EXAMPLES")
    print("="*70)
    
    # Example 1: Calculate switching price
    print("\n1️⃣ CALCULATE SWITCHING PRICE:")
    print("   Usage: switching_data = calculate_switching_price(plants_df)")
    
    # Example 2: Interpret results
    print("\n2️⃣ INTERPRET SWITCHING PRICE:")
    print("   Usage: interpretation = interpret_switching_price(50, switching_data)")
    
    # Example 3: BI Export
    print("\n3️⃣ PREPARE BI-READY EXPORT:")
    print("   Usage: bi_data = prepare_bi_export(summary_df)")
    
    # Example 4: Enhanced summary
    print("\n4️⃣ ADD SWITCHING ANALYSIS TO SUMMARY:")
    print("   Usage: enhanced_summary = add_switching_analysis_to_summary(summary_df, plants_df)")
    
    print("\n" + "="*70)
    
    # Run validation
    validate_switching_price_calculation()


# ===== INTEGRATION NOTES =====
"""
TO INTEGRATE INTO power_market_analyzer_fixed.py:

1. Copy this entire file content to the END of power_market_analyzer_fixed.py
   (after the existing visualization functions, before if __name__ == "__main__")

2. In the main execution section, add:
   
   # After creating summary_df, add:
   summary_df = add_switching_analysis_to_summary(summary_df, plants)
   
   # After saving CSV, add:
   bi_ready_df = prepare_bi_export(summary_df)
   bi_ready_df.to_csv(os.path.join(OUTPUT_DIR, 'bi_ready_export.csv'), index=False)
   print(f"   ✅ Saved BI-ready export")

3. No other modifications needed - all functions are standalone and modular!
"""
