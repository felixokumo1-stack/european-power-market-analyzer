# =====================================================================
# EUROPEAN POWER MARKET ANALYZER - STREAMLIT WEB APP (HYBRID VERSION)
# Combines: Interactive Plotly + Static Matplotlib + Data Tables
# UPDATED: Multiple fallback paths for Streamlit Cloud deployment
# =====================================================================

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import os
import sys
from PIL import Image

# Import analysis engine
try:
    import power_market_analyzer as pma
except ImportError:
    st.error("❌ Could not import power_market_analyzer module")
    st.stop()

# ===== PAGE CONFIGURATION =====

st.set_page_config(
    page_title="European Power Market Analyzer",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== CUSTOM CSS =====

st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stMetric {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        color: white;
    }
    .stMetric label {
        color: white !important;
        font-weight: bold;
    }
    .stMetric [data-testid="stMetricValue"] {
        color: white;
        font-size: 28px;
    }
    h1 {
        color: #1f77b4;
        font-family: 'Arial Black', sans-serif;
        text-align: center;
        padding: 20px 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    h2 {
        color: #2c3e50;
        border-bottom: 3px solid #3498db;
        padding-bottom: 10px;
        margin-top: 30px;
    }
    </style>
    """, unsafe_allow_html=True)

# ===== DIAGNOSTIC SECTION (OPTIONAL - CAN BE TOGGLED) =====

def show_diagnostic_info():
    """Show diagnostic information for troubleshooting"""
    with st.expander("🔍 Diagnostic Information (Click to expand)", expanded=False):
        st.subheader("System Information")
        st.write(f"**Python Version:** {sys.version}")
        st.write(f"**Current Working Directory:** `{os.getcwd()}`")
        
        st.subheader("File System")
        try:
            root_files = os.listdir('.')
            st.write(f"**Files in root directory:** {root_files}")
            
            # Check for Data folder
            if os.path.exists('Data'):
                st.success("✅ Data folder found!")
                data_files = os.listdir('Data')
                st.write(f"**Files in Data folder:** {data_files}")
            else:
                st.warning("⚠️ Data folder not found in root directory")
                
                # Check alternative locations
                alt_locations = ['data', './Data', './data', '../Data']
                for loc in alt_locations:
                    if os.path.exists(loc):
                        st.info(f"Found Data at alternative location: {loc}")
                        st.write(f"Files: {os.listdir(loc)}")
        except Exception as e:
            st.error(f"Error accessing file system: {e}")
        
        st.subheader("Module Paths")
        if 'pma' in dir():
            st.write(f"**power_market_analyzer location:** {pma.__file__ if hasattr(pma, '__file__') else 'N/A'}")
            st.write(f"**DATA_DIR configured as:** {pma.DATA_DIR if hasattr(pma, 'DATA_DIR') else 'N/A'}")

# ===== CACHED DATA LOADING WITH ERROR HANDLING =====

@st.cache_data
def load_data():
    """Load plant and scenario data with comprehensive error handling"""
    try:
        plants = pma.load_plant_database()
        scenarios = pma.load_scenarios()
        
        # Validate data
        if plants is None:
            st.error("❌ Plant database failed to load")
            st.warning("**Possible causes:**")
            st.write("1. Data folder is missing")
            st.write("2. CSV file 'German_Power_Plant_Database_2024_CORRECTED.csv' not found")
            st.write("3. File encoding issue")
            st.write("\n**Please check the diagnostic information below:**")
            show_diagnostic_info()
            return None, None
        
        if scenarios is None:
            st.error("❌ Scenarios database failed to load")
            st.warning("**Possible causes:**")
            st.write("1. Data folder is missing")
            st.write("2. CSV file 'Market_Scenarios_2024.csv' not found")
            st.write("3. File encoding issue")
            st.write("\n**Please check the diagnostic information below:**")
            show_diagnostic_info()
            return None, None
        
        return plants, scenarios
        
    except Exception as e:
        st.error(f"❌ Unexpected error during data loading: {str(e)}")
        st.write("**Error details:**")
        st.code(str(e))
        show_diagnostic_info()
        return None, None

@st.cache_data
def run_all_scenarios_cached(_plants_df, _scenarios_df):
    """Run all scenarios and cache results"""
    try:
        all_results = pma.run_all_scenarios(_plants_df, _scenarios_df)
        summary_df = pma.create_summary_dataframe(all_results)
        return all_results, summary_df
    except Exception as e:
        st.error(f"Error running scenarios: {str(e)}")
        return None, None

@st.cache_data
def generate_all_charts(_all_results, _summary_df, _plants_df):
    """Generate matplotlib charts once"""
    try:
        pma.create_all_visualizations(_all_results, _summary_df, _plants_df)
        return True
    except Exception as e:
        st.error(f"Error generating charts: {str(e)}")
        return False

# ===== INTERACTIVE PLOTLY CHARTS =====

def create_interactive_merit_order(dispatch_df, demand_mw, market_price, scenario_name):
    """Create interactive Plotly merit order curve"""
    
    dispatch_df = dispatch_df.copy()
    dispatch_df['Cumulative_Start'] = dispatch_df['Available_Capacity_MW'].cumsum().shift(1).fillna(0)
    dispatch_df['Cumulative_End'] = dispatch_df['Available_Capacity_MW'].cumsum()
    
    fig = go.Figure()
    
    color_map = {
        'Wind': '#3498db', 'Solar': '#f39c12', 'Hydro': '#1abc9c',
        'Gas': '#e74c3c', 'Coal': '#34495e', 'Gas Peaker': '#c0392b',
        'Biomass': '#27ae60'
    }
    
    for idx, row in dispatch_df.iterrows():
        if row['Is_Dispatched']:
            color = color_map.get(row['Technology'], '#95a5a6')
            
            fig.add_trace(go.Scatter(
                x=[row['Cumulative_Start'], row['Cumulative_End']],
                y=[row['SRMC_EUR_MWh'], row['SRMC_EUR_MWh']],
                mode='lines',
                line=dict(color=color, width=3),
                name=row['Technology'],
                showlegend=False,
                hovertemplate=f"<b>{row['Plant_Name']}</b><br>" +
                             f"Technology: {row['Technology']}<br>" +
                             f"SRMC: €{row['SRMC_EUR_MWh']:.2f}/MWh<br>" +
                             f"Capacity: {row['Dispatched_Capacity_MW']:.0f} MW<br>" +
                             "<extra></extra>"
            ))
            
            if idx > 0:
                prev_price = dispatch_df.iloc[idx-1]['SRMC_EUR_MWh']
                fig.add_trace(go.Scatter(
                    x=[row['Cumulative_Start'], row['Cumulative_Start']],
                    y=[prev_price, row['SRMC_EUR_MWh']],
                    mode='lines',
                    line=dict(color=color, width=3),
                    showlegend=False,
                    hoverinfo='skip'
                ))
    
    fig.add_vline(x=demand_mw, line_dash="dash", line_color="red", line_width=2,
                  annotation_text=f"Demand: {demand_mw:,.0f} MW")
    fig.add_hline(y=market_price, line_dash="dash", line_color="purple", line_width=2,
                  annotation_text=f"Market Price: €{market_price:.2f}/MWh")
    
    fig.update_layout(
        title=f"Merit Order Curve - {scenario_name}",
        xaxis_title="Cumulative Capacity (MW)",
        yaxis_title="SRMC (€/MWh)",
        hovermode='closest',
        height=600,
        showlegend=False,
        plot_bgcolor='white'
    )
    
    return fig

def create_interactive_generation_mix(results, scenario_name):
    """Create interactive pie chart"""
    
    gen_by_tech = results['generation_by_technology']
    technologies = list(gen_by_tech.keys())
    generation = list(gen_by_tech.values())
    
    color_map = {
        'Wind': '#3498db', 'Solar': '#f39c12', 'Hydro': '#1abc9c',
        'Gas': '#e74c3c', 'Coal': '#34495e', 'Gas Peaker': '#c0392b',
        'Biomass': '#27ae60'
    }
    colors = [color_map.get(tech, '#95a5a6') for tech in technologies]
    
    fig = go.Figure(data=[go.Pie(
        labels=technologies,
        values=generation,
        marker=dict(colors=colors),
        textinfo='label+percent',
        hovertemplate="<b>%{label}</b><br>Generation: %{value:,.0f} MW<br><extra></extra>"
    )])
    
    fig.update_layout(title=f"Generation Mix - {scenario_name}", height=500)
    
    return fig

# ===== ABOUT SECTION =====

def show_about_section():
    """Display project information and methodology"""
    with st.expander("ℹ️ About This Dashboard", expanded=False):
        st.markdown("## 📖 About the Project")

        # 1. Project Overview
        st.markdown("### 🎯 Project Overview")
        st.write("""
This platform provides a high-fidelity simulation of **European Power Market Dynamics** through a 
**Bottom-Up Merit Order Dispatch** model. By simulating the competition between various generation 
technologies, the tool quantifies how fuel prices, carbon taxes, and renewable penetration drive 
electricity price formation in a zonal market.
""")

        st.markdown("---")

        # 2. Methodology
        st.markdown("### 📊 Economic Dispatch Methodology")
        st.write("The model utilizes the **Merit Order Principle**, ranking plants by their **Short-Run Marginal Cost (SRMC)**:")

        # Professional Formula using LaTeX
        st.latex(r"SRMC\ [€/MWh] = \frac{Fuel\ Price}{Efficiency} + (Carbon\ Price \times Emission\ Factor) + VOM")

        st.write("""
**Key Principles:**
* **Optimal Dispatch:** The system schedules the cheapest available units first to minimize total system costs.
* **Market Clearing:** The most expensive plant required to satisfy the demand acts as the **Marginal Plant**, setting the clearing price for the entire market.
""")

        st.markdown("---")

        # 3. Key Features
        st.markdown("### 🔑 Key Features")
        st.markdown("""
- **Granular Asset Database:** 40 modeled power plants across 7 technologies (Solar, Wind, Gas, Coal, Hydro, Biomass, Lignite).
- **Dynamic Scenario Engine:** 10 pre-configured scenarios simulating winter peaks, high-renewable summer days, and supply shocks.
- **Environmental Tracking:** Real-time calculation of total CO₂ emissions and grid carbon intensity (g/kWh).
- **Interactive Analytics:** Advanced Plotly-based visualizations for deep-dive sensitivity analysis.
""")

        st.markdown("---")

        # 4. Data Attribution
        st.markdown("### 📚 Data Attribution & Sources")
        st.caption("📍 **Data Scope:** This analysis is based on 2024 German Power Market fundamentals, with plant-level data and load profiles synthesized from Fraunhofer ISE, SMARD.de, and ENTSO-E.")
        st.markdown("""
- **Generation Capacities:** [Fraunhofer ISE Energy-Charts](https://www.energy-charts.info)
- **Market Load & Demand:** [SMARD.de / Bundesnetzagentur](https://www.smard.de)
- **Commodity Pricing:** [EEX Group](https://www.eex.com)
""")

        st.markdown("---")

        # 5. Author Information
        st.markdown("### 👨‍💻 Developed By")
        st.write("**Felix Okumo**")
        st.write("*MSc Mechanical Engineering Candidate | Sustainable Energy Systems*")
        st.write("Ruhr University Bochum (RUB), Germany")

        # Arrangement of Contact Links in one line
        st.markdown("""
📧 [felix.1.okumo@gmail.com](mailto:felix.1.okumo@gmail.com) | 
💼 [LinkedIn](https://www.linkedin.com/in/felix-okumo) | 
📂 [GitHub](https://github.com/felixokumo1-stack)
""")

        st.markdown("---")

        # 6. Tech Stack
        st.markdown("### 🛠️ Technical Architecture")
        st.code("Python | Pandas | NumPy | Matplotlib | Plotly | Streamlit", language=None)

        # Excel download button
        excel_path = "Excel/European_Power_Market_Model.xlsx"
        if os.path.exists(excel_path):
            with open(excel_path, "rb") as file:
                st.download_button(
                    label="📊 Download Original Excel Prototype",
                    data=file,
                    file_name="European_Power_Market_Model.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.info("📊 Excel prototype not available in this deployment")

# ===== MAIN APP =====

def main():
    
    # Header
    st.title("⚡ European Power Market Analyzer ⚡")
    st.markdown("### 🇩🇪 German Zonal Dispatch Simulator")
    st.markdown("### Interactive Merit Order Dispatch & Scenario Analysis Dashboard")
    st.caption("📍 **Data Scope:** This analysis is based on 2024 German Power Market fundamentals, with plant-level data and load profiles synthesized from Fraunhofer ISE, SMARD.de, and ENTSO-E.")
    st.markdown("---")
    
    # About section
    show_about_section()
    
    st.markdown("---")
    
    # Load data with error handling
    with st.spinner("🔄 Loading market data..."):
        plants, scenarios = load_data()
    
    # Check if data loaded successfully
    if plants is None or scenarios is None:
        st.error("❌ Failed to load data. Please check your Data folder configuration.")
        st.warning("**Quick Fix:**")
        st.write("1. Ensure you have a 'Data' folder in your repository root")
        st.write("2. The Data folder should contain:")
        st.code("""
Data/
  ├── German_Power_Plant_Database_2024_CORRECTED.csv
  └── Market_Scenarios_2024.csv
        """)
        st.write("3. Commit and push the Data folder to GitHub")
        st.write("4. Redeploy or reboot your Streamlit app")
        
        # Show diagnostic info
        show_diagnostic_info()
        
        st.stop()
    
    # Success message
    st.success("✅ Data loaded successfully!")
    
    # Sidebar
    st.sidebar.header("🎛️ Control Panel")
    st.sidebar.markdown("---")
    
    # Mode selection
    app_mode = st.sidebar.radio(
        "Select Dashboard Mode",
        ["🎯 Interactive Analysis", "📊 Static Reports", "📋 Data Explorer"]
    )
    
    # Run analysis once
    with st.spinner("🔄 Running market dispatch scenarios..."):
        all_results, summary_df = run_all_scenarios_cached(plants, scenarios)
    
    if all_results is None or summary_df is None:
        st.error("❌ Failed to run scenarios")
        st.stop()
    
    # ===== MODE 1: INTERACTIVE ANALYSIS =====
    
    if app_mode == "🎯 Interactive Analysis":
        
        scenario_names = scenarios['Scenario_Name'].tolist()
        selected_scenario = st.sidebar.selectbox("Select Scenario", scenario_names, index=0)
        
        scenario_data = scenarios[scenarios['Scenario_Name'] == selected_scenario].iloc[0]
        
        # Scenario parameters
        st.sidebar.markdown("### 📋 Scenario Parameters")
        st.sidebar.metric("Demand", f"{scenario_data['Demand_MW']:,.0f} MW")
        st.sidebar.metric("Carbon Price", f"€{scenario_data['Carbon_Price_EUR_ton']:.0f}/ton")
        st.sidebar.metric("Wind Availability", f"{scenario_data['Wind_Availability_Percent']:.0f}%")
        st.sidebar.metric("Solar Availability", f"{scenario_data['Solar_Availability_Percent']:.0f}%")
        
        # Get results for selected scenario
        result = next((r for r in all_results if r['scenario_name'] == selected_scenario), None)
        
        if result:
            # KPIs
            st.header(f"📊 Results: {selected_scenario}")
            col1, col2, col3, col4, col5 = st.columns(5)
            
            col1.metric("Market Price", f"€{result['market_price_eur_mwh']:.2f}/MWh")
            col2.metric("Total Emissions", f"{result['total_emissions_tons']:,.0f} tons")
            col3.metric("Renewable Share", f"{result['renewable_share_pct']:.1f}%")
            col4.metric("Producer Surplus", f"€{result['total_profit_eur']:,.0f}")
            col5.metric("Demand Status", "✅ Met" if result['demand_met'] else "❌ Shortage")
            
            st.markdown("---")
            
            # Interactive charts
            col_a, col_b = st.columns([1.2, 1])
            
            with col_a:
                st.subheader("📈 Interactive Merit Order Curve")
                merit_fig = create_interactive_merit_order(
                    result['dispatch_df'],
                    result['demand_mw'],
                    result['market_price_eur_mwh'],
                    selected_scenario
                )
                st.plotly_chart(merit_fig, use_container_width=True)
                st.info(f"**Marginal Plant:** {result['marginal_plant_name']} ({result['marginal_technology']})")
            
            with col_b:
                st.subheader("🥧 Generation Mix")
                pie_fig = create_interactive_generation_mix(result, selected_scenario)
                st.plotly_chart(pie_fig, use_container_width=True)
                
                # Generation table
                gen_df = pd.DataFrame(list(result['generation_by_technology'].items()),
                                     columns=['Technology', 'Generation (MW)'])
                gen_df['Share (%)'] = (gen_df['Generation (MW)'] / result['demand_mw'] * 100).round(1)
                st.dataframe(gen_df, hide_index=True, use_container_width=True)
    
    # ===== MODE 2: STATIC REPORTS =====
    
    elif app_mode == "📊 Static Reports":
        
        st.header("📊 Generated Analysis Reports")
        
        # Generate charts if needed
        with st.spinner("🔄 Generating visualization reports..."):
            charts_generated = generate_all_charts(all_results, summary_df, plants)
        
        if not charts_generated:
            st.warning("⚠️ Some charts may not be available")
        
        charts_path = pma.CHARTS_DIR

        # Overview section
        st.subheader("🌍 Global Market Overview")
        col1, col2 = st.columns(2)
        
        with col1:
            chart_path = os.path.join(charts_path, 'scenario_comparison_dashboard.png')
            if os.path.exists(chart_path):
                st.image(chart_path, caption="Scenario Comparison Dashboard")
            else:
                st.warning("Chart not available")
            
            chart_path = os.path.join(charts_path, 'carbon_price_sensitivity.png')
            if os.path.exists(chart_path):
                st.image(chart_path, caption="Carbon Price Sensitivity")
            else:
                st.warning("Chart not available")
        
        with col2:
            chart_path = os.path.join(charts_path, 'technology_stack.png')
            if os.path.exists(chart_path):
                st.image(chart_path, caption="Technology Stack Evolution")
            else:
                st.warning("Chart not available")
            
            chart_path = os.path.join(charts_path, 'emissions_intensity_comparison.png')
            if os.path.exists(chart_path):
                st.image(chart_path, caption="Emissions Intensity vs EU Targets")
            else:
                st.warning("Chart not available")
        
        st.markdown("---")
        
        # Scenario-specific section
        st.subheader("🔍 Scenario-Specific Analysis")
        
        selected_view = st.selectbox(
            "Select Scenario",
            ['Base_Load_Summer', 'Peak_Load_Winter', 'Extreme_Peak', 'High_Wind_Day']
        )
        
        col_a, col_b = st.columns([2, 1])
        
        with col_a:
            merit_path = os.path.join(charts_path, f'merit_order_{selected_view}.png')
            if os.path.exists(merit_path):
                st.image(merit_path, use_container_width=True, caption=f"Merit Order - {selected_view}")
            else:
                st.warning(f"Merit order chart for {selected_view} not available")
        
        with col_b:
            mix_path = os.path.join(charts_path, f'generation_mix_{selected_view}.png')
            if os.path.exists(mix_path):
                st.image(mix_path, use_container_width=True, caption=f"Generation Mix - {selected_view}")
            else:
                st.warning(f"Generation mix chart for {selected_view} not available")
    
    # ===== MODE 3: DATA EXPLORER =====
    
    elif app_mode == "📋 Data Explorer":
        
        st.header("📋 Comprehensive Data Analysis")
        
        # Summary statistics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Scenarios", len(summary_df))
        col2.metric("Avg Market Price", f"€{summary_df['Market_Price_EUR_MWh'].mean():.2f}/MWh")
        col3.metric("Avg Renewable Share", f"{summary_df['Renewable_Share_%'].mean():.1f}%")
        col4.metric("Total CO₂ Emissions", f"{summary_df['Total_Emissions_tons'].sum():,.0f} tons")
        
        st.markdown("---")
        
        # Full data table
        st.subheader("📊 Complete Scenario Results")
        
        # Format the dataframe
        display_df = summary_df.copy()
        st.dataframe(
            display_df.style.format({
                'Market_Price_EUR_MWh': '€{:.2f}',
                'Renewable_Share_%': '{:.1f}%',
                'Total_Emissions_tons': '{:,.0f}',
                'Carbon_Intensity_g_kWh': '{:.1f}',
                'Producer_Surplus_EUR': '€{:,.0f}'
            }),
            use_container_width=True,
            height=400
        )
        
        # Download button
        csv = summary_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Complete Results (CSV)",
            data=csv,
            file_name="power_market_analysis.csv",
            mime="text/csv"
        )
        
        # Key insights
        st.markdown("---")
        st.subheader("🔑 Key Insights")
        
        col_i1, col_i2 = st.columns(2)
        
        with col_i1:
            st.markdown("**💰 Price Analysis:**")
            min_price = summary_df['Market_Price_EUR_MWh'].min()
            max_price = summary_df['Market_Price_EUR_MWh'].max()
            min_scenario = summary_df.loc[summary_df['Market_Price_EUR_MWh'].idxmin(), 'Scenario_Name']
            max_scenario = summary_df.loc[summary_df['Market_Price_EUR_MWh'].idxmax(), 'Scenario_Name']
            
            st.write(f"- **Range:** €{min_price:.2f} - €{max_price:.2f}/MWh")
            st.write(f"- **Lowest:** {min_scenario} (€{min_price:.2f})")
            st.write(f"- **Highest:** {max_scenario} (€{max_price:.2f})")
        
        with col_i2:
            st.markdown("**♻️ Renewable Energy:**")
            avg_renewable = summary_df['Renewable_Share_%'].mean()
            max_renewable = summary_df['Renewable_Share_%'].max()
            
            st.write(f"- **Average Share:** {avg_renewable:.1f}%")
            st.write(f"- **Maximum Share:** {max_renewable:.1f}%")
            st.write(f"- **Scenarios with 100% RE:** {len(summary_df[summary_df['Renewable_Share_%'] == 100])}")
    
    # Enhanced Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; padding: 30px; background: #f8f9fa; border-radius: 10px;'>
        <h3 style='color: #1f77b4; margin-bottom: 15px;'>⚡ European Power Market Analyzer</h3>
        <p style='color: #555; font-size: 16px;'><b>Merit Order Dispatch Model</b> | German Power Market Analysis (2024)</p>
        <p style='color: #777; margin-top: 10px;'>
            Built with Python, Streamlit, Plotly | 
            <a href='https://github.com/felixokumo1-stack' target='_blank'>📂 View Source Code</a> | 
            <a href='https://www.linkedin.com/in/felix-okumo' target='_blank'>💼 Connect on LinkedIn</a>
        </p>
        <p style='color: #999; font-size: 14px; margin-top: 15px;'>
            © 2026 Felix Okumo | Technical Portfolio: Energy Economics & Market Simulation
        </p>
    </div>
""", unsafe_allow_html=True)

# ===== RUN APP =====

if __name__ == "__main__":
    main()
