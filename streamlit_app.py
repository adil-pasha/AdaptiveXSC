import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.models.loader import DataLoader
from src.xai.shap_explain import SHAPExplainer, generate_plain_language_explanation
from src.sim.simulator import WhatIfSimulator, ALLOWED_SCENARIO_VARS
from src.sim.decision import DecisionEngine

# 2. PAGE CONFIGURATION
st.set_page_config(
    page_title="AdaptiveXSC",
    page_icon="📦",
    layout="wide"
)

st.title("AdaptiveXSC")
st.subheader("Explainable Supply Chain Decision Intelligence")

# 1. STREAMLIT INITIALIZATION (Data Loading)
@st.cache_resource
def load_data_and_model():
    return DataLoader.load()

try:
    model, df_test = load_data_and_model()
except Exception as e:
    st.error(f"Failed to load model and data: {str(e)}")
    st.stop()

# 3. ONBOARDING
with st.expander("Welcome to AdaptiveXSC", expanded=False):
    st.write("""
    - **AdaptiveXSC** forecasts future demand.
    - **SHAP** explains which available model inputs influenced the forecast. Under the model, specific inputs (like promotion status) are associated with higher or lower forecasts; these are model explanations, not causal claims.
    - **What-If analysis** allows the evaluator to test hypothetical operational changes to see how the model and rules respond.
    - **The Decision Engine** provides transparent rule-based operational states based on the forecasts and inventory metrics.
    - **Human decisions** will eventually be collected for research analysis.
    """)

# 4. EVALUATOR ID
st.markdown("### Evaluator Identity")
if "evaluator_id" not in st.session_state:
    st.session_state.evaluator_id = ""

evaluator_input = st.text_input("Evaluator ID", value=st.session_state.evaluator_id, placeholder="Enter your evaluator code (e.g. EVAL-001)")

if evaluator_input.strip() != "":
    st.session_state.evaluator_id = evaluator_input.strip()
    st.success(f"Evaluator: {st.session_state.evaluator_id}")
else:
    st.info("An evaluator ID will be required before submission in a later phase.")
    st.session_state.evaluator_id = ""

st.markdown("---")

# 5. DIVERSITY FILTER
st.markdown("### Observation Selection")
col1, col2, col3, col4 = st.columns(4)

with col1:
    promo_filter = st.selectbox(
        "Promotion Filter",
        options=["Any", "Promotion Active", "Promotion Inactive"]
    )

# Filter dataframe based on promo
df_filtered = df_test.copy()
if promo_filter == "Promotion Active":
    df_filtered = df_filtered[df_filtered['Promotion_Flag'] == 1]
elif promo_filter == "Promotion Inactive":
    df_filtered = df_filtered[df_filtered['Promotion_Flag'] == 0]

if df_filtered.empty:
    st.warning("No observations found matching the selected filters.")
    st.stop()

# 6. CASCADING OBSERVATION SELECTORS
# Ensure valid selections
if "selected_warehouse" not in st.session_state:
    st.session_state.selected_warehouse = None
if "selected_sku" not in st.session_state:
    st.session_state.selected_sku = None
if "selected_date" not in st.session_state:
    st.session_state.selected_date = None

# Warehouse
wh_options = list(df_filtered['Warehouse_ID'].unique())
if st.session_state.selected_warehouse not in wh_options:
    st.session_state.selected_warehouse = wh_options[0]

with col2:
    selected_wh = st.selectbox("Warehouse", options=wh_options, index=wh_options.index(st.session_state.selected_warehouse))
    st.session_state.selected_warehouse = selected_wh

# SKU
df_wh = df_filtered[df_filtered['Warehouse_ID'] == selected_wh]
sku_options = list(df_wh['SKU_ID'].unique())
if st.session_state.selected_sku not in sku_options:
    st.session_state.selected_sku = sku_options[0]

with col3:
    selected_sku = st.selectbox("SKU", options=sku_options, index=sku_options.index(st.session_state.selected_sku))
    st.session_state.selected_sku = selected_sku

# Date
df_sku = df_wh[df_wh['SKU_ID'] == selected_sku]
# Convert dates to string format for display
date_options = list(df_sku['Date'].dt.strftime('%Y-%m-%d').unique())
if st.session_state.selected_date not in date_options:
    st.session_state.selected_date = date_options[-1] if date_options else None

with col4:
    selected_date = st.selectbox("Date", options=date_options, index=date_options.index(st.session_state.selected_date))
    st.session_state.selected_date = selected_date

# OBSERVATION CHANGE TRACKING
current_obs_id = f"{selected_wh}_{selected_sku}_{selected_date}"
if "last_obs_id" not in st.session_state or st.session_state.last_obs_id != current_obs_id:
    # Reset scenario controls when observation changes
    for k in ALLOWED_SCENARIO_VARS:
        st.session_state.pop(f"scen_{k}", None)
    st.session_state.last_obs_id = current_obs_id

st.markdown("---")

# 7. SELECTED OBSERVATION SUMMARY
date_obj = pd.to_datetime(selected_date)
df_final_row = df_sku[df_sku['Date'] == date_obj]

if df_final_row.empty:
    st.warning("Observation not found.")
    st.stop()

row = df_final_row.iloc[0]

st.markdown("### Selected Observation Summary")
sum_col1, sum_col2, sum_col3, sum_col4 = st.columns(4)
sum_col1.metric("SKU", row['SKU_ID'])
sum_col2.metric("Warehouse", row['Warehouse_ID'])
sum_col3.metric("Date", selected_date)
sum_col4.metric("Promotion Flag", "Active" if row['Promotion_Flag'] == 1 else "Inactive")

sum_col5, sum_col6, sum_col7, sum_col8 = st.columns(4)
sum_col5.metric("Inventory Level", f"{row['Inventory_Level']:.1f}")
sum_col6.metric("Reorder Point", f"{row['Reorder_Point']:.1f}")
sum_col7.metric("Order Quantity", f"{row['Order_Quantity']:.1f}")
sum_col8.metric("Actual Units Sold", f"{row['Units_Sold']:.1f}")

st.markdown("---")

# FORECAST & SHAP INTEGRATION
try:
    shap_explainer = SHAPExplainer(model)
    local_expl = shap_explainer.get_local_explanation(df_final_row, actual_value=float(row['Units_Sold']))
    
    if not local_expl.get('reconstruction_verified', False):
        st.error("SHAP Reconstruction failed tolerance check. Explanation aborted.")
        st.stop()
        
except Exception as e:
    st.error(f"Failed to generate forecast and SHAP explanation: {str(e)}")
    st.stop()

# BASELINE FORECAST
st.markdown("## Baseline Forecast")
base_col1, base_col2, base_col3 = st.columns(3)
base_col1.metric("Forecast Demand", f"{local_expl['predicted_Units_Sold']:.2f} units")
base_col2.metric("Actual Demand", f"{local_expl['actual_Units_Sold']:.2f} units")
base_col3.metric("Forecast Error", f"{local_expl['prediction_error']:.2f} units")

# SHAP VISUALIZATION
st.markdown("## Forecast Drivers (SHAP Explanation)")
plain_text = generate_plain_language_explanation(local_expl)
st.write(plain_text)

contribs = local_expl['feature_contributions']
contribs_sorted = sorted(contribs, key=lambda x: abs(x['shap_value']), reverse=False)[-5:]

fig = go.Figure(go.Bar(
    x=[c['shap_value'] for c in contribs_sorted],
    y=[c['feature'] for c in contribs_sorted],
    orientation='h',
    marker_color=['green' if c['shap_value'] > 0 else 'red' for c in contribs_sorted]
))
fig.update_layout(
    margin=dict(l=0, r=0, t=30, b=0),
    height=300,
    xaxis_title="Contribution to Forecast (Units)",
    title="Top 5 Feature Contributions (SHAP)"
)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# WHAT-IF SCENARIO ANALYSIS
st.markdown("## What-If Scenario Analysis")
st.info("This section allows you to test how the existing forecasting model responds to hypothetical changes in selected inputs. These are model-based counterfactuals, not causal predictions.")

if st.button("Reset Scenario"):
    for k in ALLOWED_SCENARIO_VARS:
        st.session_state.pop(f"scen_{k}", None)
    st.rerun()

changes = {}
scen_cols = st.columns(4)
for i, k in enumerate(sorted(list(ALLOWED_SCENARIO_VARS))):
    base_val = float(row[k])
    col = scen_cols[i % 4]
    
    with col:
        if k == 'Promotion_Flag':
            if f"scen_{k}" not in st.session_state:
                st.session_state[f"scen_{k}"] = bool(base_val)
            val = st.toggle(f"{k} (Base: {bool(base_val)})", key=f"scen_{k}")
            if float(val) != base_val:
                changes[k] = float(val)
        else:
            if f"scen_{k}" not in st.session_state:
                st.session_state[f"scen_{k}"] = base_val
            val = st.number_input(f"{k} (Base: {base_val:.2f})", min_value=0.0, key=f"scen_{k}", format="%.2f")
            if val != base_val:
                changes[k] = val

simulator = WhatIfSimulator(model)
try:
    sim_results = simulator.simulate(df_final_row, changes)
except Exception as e:
    st.error(f"Simulator error: {str(e)}")
    st.stop()

st.markdown("### Baseline vs Scenario")
diff_col1, diff_col2, diff_col3, diff_col4 = st.columns(4)
diff_col1.metric("Baseline Forecast", f"{sim_results['baseline_forecast']:.2f} units")
diff_col2.metric("Scenario Forecast", f"{sim_results['scenario_forecast']:.2f} units")

diff = sim_results['forecast_difference']
pct_diff = sim_results['percentage_difference']

diff_color = "normal" if abs(diff) > 1e-4 else "off"
diff_col3.metric("Forecast Difference", f"{diff:+.2f} units", delta=f"{diff:+.2f}", delta_color=diff_color)
if pct_diff is not None:
    pct_color = "normal" if abs(pct_diff) > 1e-4 else "off"
    diff_col4.metric("Percentage Difference", f"{pct_diff:+.2f}%", delta=f"{pct_diff:+.2f}%", delta_color=pct_color)
else:
    diff_col4.metric("Percentage Difference", "N/A")

st.markdown("### Forecast Change Contributors")
st.write(f"Under the model, this hypothetical change produces an estimated forecast change of {diff:+.2f} units.")
has_contributors = False
for c in sim_results['change_contributors']:
    if abs(c['contribution_diff']) > 1e-4:
        has_contributors = True
        st.write(f"- Under the model, changing **{c['feature']}** is associated with an estimated forecast difference of {c['contribution_diff']:+.2f} units.")

if not has_contributors:
    st.write("No significant forecast change contributors.")

st.markdown("---")

# DECISION ENGINE INTEGRATION
decision_engine = DecisionEngine(high_demand_multiplier=1.5)

# Baseline Evaluation
base_eval = decision_engine.evaluate(
    forecast=sim_results['baseline_forecast'],
    inventory_level=float(row['Inventory_Level']),
    reorder_point=float(row['Reorder_Point']),
    order_quantity=float(row['Order_Quantity']),
    recent_demand=float(row['Rolling_7d_Mean_Units_Sold'])
)

st.markdown("## Baseline Decision")
dec_col1, dec_col2 = st.columns(2)
dec_col1.metric("Decision State", base_eval['decision_state'])
dec_col2.metric("Severity", base_eval['severity'])

dec_col3, dec_col4, dec_col5, dec_col6 = st.columns(4)
dec_col3.metric("Forecast", f"{base_eval['forecast']:.2f}")
dec_col4.metric("Inventory Level", f"{base_eval['inventory_level']:.2f}")
dec_col5.metric("Reorder Point", f"{base_eval['reorder_point']:.2f}")
dec_col6.metric("Order Quantity", f"{base_eval['order_quantity']:.2f}")

st.markdown("#### Triggered Rules")
if not base_eval['triggered_rules'] and base_eval['decision_state'] == 'NORMAL':
    st.write("No decision rules triggered.")
else:
    for rule in base_eval['triggered_rules']:
        st.write(f"- `{rule}`")

st.markdown("---")
st.markdown("## Scenario Decision")

# Scenario Evaluation
scen_eval = decision_engine.evaluate(
    forecast=sim_results['scenario_forecast'],
    inventory_level=float(sim_results['scenario_features'].get('Lag_1_Inventory_Level', row['Inventory_Level'])),
    reorder_point=float(row['Reorder_Point']),
    order_quantity=float(sim_results['scenario_features'].get('Lag_1_Order_Quantity', row['Order_Quantity'])),
    recent_demand=float(sim_results['scenario_features'].get('Rolling_7d_Mean_Units_Sold', row['Rolling_7d_Mean_Units_Sold']))
)

comp_eval = decision_engine.evaluate_scenario_comparison(base_eval, scen_eval)
scen_decision = comp_eval['scenario_decision']

scen_dec_col1, scen_dec_col2, scen_dec_col3 = st.columns(3)
scen_dec_col1.metric("Scenario Forecast", f"{scen_decision['forecast']:.2f} units")
scen_dec_col2.metric("Scenario Decision State", scen_decision['decision_state'])
scen_dec_col3.metric("Scenario Severity", scen_decision['severity'])

st.markdown("#### Triggered Rules")
if not scen_decision['triggered_rules'] and scen_decision['decision_state'] == 'NORMAL':
    st.write("No decision rules triggered.")
else:
    for rule in scen_decision['triggered_rules']:
        st.write(f"- `{rule}`")

st.markdown("#### Scenario Risk")
if 'scenario_escalates_severity' in scen_decision['triggered_rules']:
    st.error("`scenario_escalates_severity`")
else:
    st.success("No escalation relative to the baseline decision.")

st.markdown("---")
st.markdown("## Rule-Based Decision Explanation")
st.info(scen_decision['explanation'])

st.markdown("---")

# HUMAN DECISION SECTION
st.markdown("## Human Decision")
st.write("You are reviewing the model's recommendation for this selected supply-chain observation.")
st.write("- **ACCEPT:** Accept the system's decision as presented.")
st.write("- **REJECT:** Reject the system's decision.")
st.write("- **OVERRIDE:** Choose a different human decision from the system's recommendation and provide a reason.")

manager_action = st.radio("Decision Action", ["ACCEPT", "REJECT", "OVERRIDE"], index=None)

override_reason = None
override_note = None

if manager_action == "OVERRIDE":
    OVERRIDE_REASONS = [
        "Supplier Delay", "Upcoming Promotion", "Local Demand Knowledge",
        "Inventory Constraint", "Data Quality Concern", 
        "Forecast Appears Too High", "Forecast Appears Too Low", "Other"
    ]
    override_reason = st.selectbox("Override Reason", options=[None] + OVERRIDE_REASONS)
    override_note = st.text_area("Override Note")

# SUBMISSION STATE PREPARATION
import hashlib
import json

scenario_applied = any(v != float(row[k]) for k, v in changes.items())
scenario_description = json.dumps(changes, sort_keys=True) if scenario_applied else "Baseline"

try:
    structured_shap = json.dumps(local_expl["feature_contributions"], sort_keys=True)
    if not local_expl["feature_contributions"]:
        raise ValueError("Empty SHAP contributions")
except Exception as e:
    st.error(f"SHAP Serialization Failed: {str(e)}")
    st.stop()

record_data = {
    "SKU_ID": str(row["SKU_ID"]),
    "Warehouse_ID": str(row["Warehouse_ID"]),
    "Date": str(date_obj.strftime("%Y-%m-%d")),
    "baseline_forecast": float(base_eval["forecast"]),
    "actual_units_sold": float(row["Units_Sold"]),
    "inventory_level": float(base_eval["inventory_level"]),
    "reorder_point": float(base_eval["reorder_point"]),
    "baseline_decision_state": str(base_eval["decision_state"]),
    "baseline_severity": str(base_eval["severity"]),
    
    "scenario_applied": bool(scenario_applied),
    "scenario_description": str(scenario_description),
    "scenario_forecast": float(scen_eval["forecast"]),
    "scenario_decision_state": str(scen_decision["decision_state"]),
    "scenario_severity": str(scen_decision["severity"]),
    
    "top_shap_drivers": structured_shap,
    
    "evaluator_id": st.session_state.evaluator_id if st.session_state.evaluator_id else "",
    "manager_action": str(manager_action) if manager_action else "",
    "override_reason": str(override_reason) if override_reason else "",
    "override_note": str(override_note) if override_note else ""
}

raw_fingerprint = {
    "sys": record_data["SKU_ID"] + record_data["Warehouse_ID"] + record_data["Date"],
    "scenario": record_data["scenario_description"],
    "act": record_data["manager_action"],
    "reason": record_data["override_reason"],
    "note": record_data["override_note"],
    "evaluator": record_data["evaluator_id"]
}
current_fingerprint = hashlib.sha256(json.dumps(raw_fingerprint, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

button_disabled = False
if "last_submitted_fingerprint" in st.session_state and st.session_state.last_submitted_fingerprint == current_fingerprint:
    button_disabled = True

if st.button("SUBMIT DECISION", disabled=button_disabled):
    if not record_data['evaluator_id']:
        st.error("Decision could not be recorded: Evaluator ID is required.")
    elif record_data['manager_action'] not in ["ACCEPT", "REJECT", "OVERRIDE"]:
        st.error("Decision could not be recorded: Please select an action.")
    elif record_data['manager_action'] == "OVERRIDE" and not record_data['override_reason']:
        st.error("Decision could not be recorded: Override Reason is required.")
    else:
        try:
            from src.audit.schema import AuditRecord
            from src.audit.logger import AuditLogger
            
            # The schema might expect evaluator_id to be strictly non-empty or None
            # If the schema validates, it will pass. If it fails, it throws ValueError.
            # Convert empty strings back to None for Optional fields if necessary:
            if not record_data['override_reason']: record_data['override_reason'] = None
            if not record_data['override_note']: record_data['override_note'] = None
            
            record = AuditRecord(**record_data)
            logger = AuditLogger()
            audit_id = logger.log_decision(record)
            
            st.session_state.last_submitted_fingerprint = current_fingerprint
            st.success(f"Decision recorded successfully. Audit ID: {audit_id}")
            st.rerun()
        except Exception as e:
            st.error(f"Decision could not be saved. Please try again. ({str(e)})")

with st.container():
    st.markdown("---")
    st.markdown("## Collection Progress")
    try:
        from src.audit.logger import AuditLogger
        stats = AuditLogger.get_collection_stats()
        
        # Row 1: Decision Metrics
        with st.container():
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f"**Total Decisions**<br><span style='font-size:24px;'>{stats.get('total', 0)}</span>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"**ACCEPT**<br><span style='font-size:24px;'>{stats.get('ACCEPT', 0)}</span>", unsafe_allow_html=True)
            with col3:
                st.markdown(f"**REJECT**<br><span style='font-size:24px;'>{stats.get('REJECT', 0)}</span>", unsafe_allow_html=True)
            with col4:
                st.markdown(f"**OVERRIDE**<br><span style='font-size:24px;'>{stats.get('OVERRIDE', 0)}</span>", unsafe_allow_html=True)
        
            st.divider()
        
            # Row 2: Unique Diversity Metrics
            col5, col6, col7 = st.columns(3)
            with col5:
                st.markdown(f"**Unique Evaluators**<br><span style='font-size:24px;'>{stats.get('unique_evaluators_count', 'N/A')}</span>", unsafe_allow_html=True)
            with col6:
                st.markdown(f"**Unique SKUs**<br><span style='font-size:24px;'>{stats.get('unique_skus_count', 0)}</span>", unsafe_allow_html=True)
            with col7:
                st.markdown(f"**Unique Warehouses**<br><span style='font-size:24px;'>{stats.get('unique_whs_count', 0)}</span>", unsafe_allow_html=True)
    except Exception as e:
        st.write("Could not load collection stats.")
