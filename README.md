\# ⚡ European Power Market Analyzer (German Zonal Focus)

\[\![Streamlit
App\](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)\](YOUR_DEPLOYED_APP_URL_HERE)
\[\![Python
3.11+\](https://img.shields.io/badge/python-3.11+-blue.svg)\](https://www.python.org/downloads/)
\[\![License:
MIT\](https://img.shields.io/badge/License-MIT-yellow.svg)\](https://opensource.org/licenses/MIT)

\## 🎯 Project Overview This platform provides a high-fidelity
simulation of \*\*European Power Market Dynamics\*\* through a
\*\*Bottom-Up Merit Order Dispatch\*\* model.

The tool utilizes verified \*\*2024 German Power Market fundamentals\*\*
to analyze how different generation technologies compete to satisfy
demand. It is designed as a technical showcase for energy economics,
carbon pricing sensitivity, and grid decarbonization analysis,
demonstrating the transition from traditional Excel modeling to
automated Python-based web applications.

\## 📈 Evolution: From Excel to Python This project originated as a
complex Excel-based analytical tool. This Streamlit extension was
developed to: \* \*\*Automate\*\* data processing and scenario
iterations. \* \*\*Enhance\*\* visualization capabilities with
interactive Plotly analytics. \* \*\*Improve Accessibility\*\* via a
cloud-based interface for stakeholders.

\*The original Excel prototype is available for download within the app
and in the \`/Excel\` directory.\*

\## 📊 Methodology: The Merit Order Dispatch The engine calculates the
\*\*Short-Run Marginal Cost (SRMC)\*\* for every power plant in the 2024
German fleet. The dispatch logic follows the European market clearing
mechanism:

1\. \*\*SRMC Calculation:\*\* \$\$SRMC\\ \[€/MWh\] = \\frac{Fuel\\
Price}{\\eta} + (Carbon\\ Price \\times Emission\\ Factor) + VOM\$\$ 2.
\*\*Economic Ranking:\*\* Assets are sorted from lowest to highest
marginal cost. 3. \*\*Market Clearing:\*\* The intersection of the
supply curve and the \*\*Residual Load\*\* determines the \*\*System
Marginal Price (SMP)\*\*.

\## 🔑 Key Features \* \*\*Granular Asset Database:\*\* 40+ modeled
plants across 7 technologies (Wind, Solar, Gas, Coal, Lignite, Hydro,
Biomass). \* \*\*2024 Scenarios:\*\* 10 pre-configured datasets
simulating winter peaks, high-renewable summer days, and supply shocks.
\* \*\*Environmental Impact:\*\* Real-time calculation of total CO₂
emissions and grid carbon intensity (g/kWh). \* \*\*Interactive
Visuals:\*\* Dynamic Merit Order \"Staircase\" charts and Technology
Stack breakdowns.

\## 🛠️ Technical Stack \* \*\*Language:\*\* Python 3.11 \* \*\*Data
Science:\*\* \`pandas\`, \`numpy\`, \`openpyxl\` \*
\*\*Visualization:\*\* \`plotly\`, \`matplotlib\` \* \*\*Web
Framework:\*\* \`streamlit\`

\## 📂 Repository Structure \`\`\`text ├── Data/ \# CSV datasets
(Plants, Scenarios, Fuel Prices) ├── Excel/ \# Original Legacy Excel
Dashboard Prototype ├── streamlit_app.py \# Main Dashboard UI & Logic
├── requirements.txt \# Python dependencies └── README.md \# Project
documentation

🚀 Installation & Local Execution

To run the simulator locally, follow these steps:

Clone the repository: git clone
\[https://github.com/felixokumo1-stack/your-repo-name.git\](https://github.com/felixokumo1-stack/your-repo-name.git)
cd your-repo-name

Install dependencies: pip install -r requirements.txt

Run the App: streamlit run streamlit_app.py

📚 Data Attribution Data synthesized from verified institutional
sources:

Generation Capacities: Fraunhofer ISE Energy-Charts

Market Load: SMARD.de / Bundesnetzagentur

Commodity Pricing: EEX Group

👨‍💻 Author Felix Okumo MSc Mechanical Engineering Student \| Sustainable
Energy Systems Ruhr University Bochum (RUB), Germany 📧
felix.1.okumo@gmail.com \| 💼 LinkedIn \| 📂 GitHub

Developed for Energy Economics & Portfolio Purposes.
