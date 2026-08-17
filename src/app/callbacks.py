from dash import Input, Output, State, html, ctx, no_update
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import json
import hashlib
from src.models.loader import DataLoader
from src.sim.simulator import WhatIfSimulator
from src.sim.decision import DecisionEngine
from src.xai.shap_explain import generate_plain_language_explanation
from src.audit.logger import AuditLogger
from src.audit.schema import AuditRecord

# Instantiate engines once
model, df_test = DataLoader.load()
simulator = WhatIfSimulator(model)
decision_engine = DecisionEngine(high_demand_multiplier=1.5)
audit_logger = AuditLogger()

def update_diversity_filters(promo_filter, selected_wh, selected_sku, selected_date):
    # 1. Filter the base dataframe
    df_filtered = df_test.copy()
    if promo_filter == 1:
        df_filtered = df_filtered[df_filtered['Promotion_Flag'] == 1]
    elif promo_filter == 0:
        df_filtered = df_filtered[df_filtered['Promotion_Flag'] == 0]
        
    if df_filtered.empty:
        return [], None, [], None, [], None

    # 2. Get valid options
    wh_options_list = df_filtered['Warehouse_ID'].unique().tolist()
    
    if selected_wh not in wh_options_list:
        selected_wh = wh_options_list[0] if wh_options_list else None
        
    # 3. Filter SKUs based on WH
    df_wh = df_filtered[df_filtered['Warehouse_ID'] == selected_wh] if selected_wh else df_filtered
    sku_options_list = df_wh['SKU_ID'].unique().tolist()
    
    if selected_sku not in sku_options_list:
        selected_sku = sku_options_list[0] if sku_options_list else None
        
    # 4. Filter Dates based on WH and SKU
    df_final = df_wh[df_wh['SKU_ID'] == selected_sku] if selected_sku else df_wh
    date_options_list = df_final['Date'].dt.strftime('%Y-%m-%d').unique().tolist()
    
    if selected_date not in date_options_list:
        selected_date = date_options_list[-1] if date_options_list else None
        
    wh_opts = [{'label': w, 'value': w} for w in wh_options_list]
    sku_opts = [{'label': s, 'value': s} for s in sku_options_list]
    date_opts = [{'label': d, 'value': d} for d in date_options_list]
    
    return wh_opts, selected_wh, sku_opts, selected_sku, date_opts, selected_date

def submit_decision(n_clicks, action, system_state, reason, note, evaluator_id):
    if not n_clicks:
        return ""
    
    if not evaluator_id or not evaluator_id.strip():
        return dbc.Alert("Error: Please enter an Evaluator ID before submitting.", color="danger")
        
    if not system_state:
        return dbc.Alert("Error: System state missing.", color="danger")
    if not action:
        return dbc.Alert("Error: Please select an action (ACCEPT, REJECT, OVERRIDE) before submitting.", color="danger")
        
    try:
        record_data = system_state.copy()
        record_data['manager_action'] = action
        record_data['evaluator_id'] = evaluator_id.strip()
        if action == 'OVERRIDE':
            if not reason:
                return dbc.Alert("Error: Override reason is required.", color="danger")
            record_data['override_reason'] = reason
            if note:
                record_data['override_note'] = note
                
        record = AuditRecord(**record_data)
        audit_id = audit_logger.log_decision(record)
        
        return dbc.Alert(f"Decision recorded successfully. Audit ID: {audit_id}", color="success")
    except Exception as e:
        return dbc.Alert(f"Error saving audit record: {str(e)}", color="danger")

def submit_feedback(n_clicks, system_state, f_type, f_text, evaluator_id):
    if not n_clicks:
        return ""
        
    if not evaluator_id or not evaluator_id.strip():
        return dbc.Alert("Error: Please enter your Evaluator ID at the top of the page before submitting feedback.", color="danger")
        
    if not system_state:
        return dbc.Alert("Error: System state missing. Please select an observation first.", color="danger")
        
    if not f_type:
        return dbc.Alert("Error: Please select a Feedback Type.", color="danger")
        
    if not f_text or not f_text.strip():
        return dbc.Alert("Error: Please enter a description.", color="danger")
        
    try:
        from src.audit.schema import FeedbackRecord
        record = FeedbackRecord(
            evaluator_id=evaluator_id.strip(),
            SKU_ID=system_state.get('SKU_ID', ''),
            Warehouse_ID=system_state.get('Warehouse_ID', ''),
            Date=system_state.get('Date', ''),
            baseline_decision_state=system_state.get('baseline_decision_state', ''),
            scenario_description=system_state.get('scenario_description', None),
            feedback_type=f_type,
            feedback_text=f_text.strip()
        )
        audit_logger.log_feedback(record)
        return dbc.Alert("Feedback submitted successfully. Thank you!", color="success")
    except ValueError as e:
        return dbc.Alert(f"Validation Error: {str(e)}", color="danger")
    except Exception as e:
        return dbc.Alert(f"System Error: {str(e)}", color="danger")

def update_dashboard(warehouse, sku, date_str, promo_val, price_pct, cost_pct, inv_pct):
    if not date_str:
        return "No data", "", go.Figure(), "No data", "No data", None, ""

    date_obj = pd.to_datetime(date_str)
    df_sub = df_test[(df_test['Warehouse_ID'] == warehouse) & 
                     (df_test['SKU_ID'] == sku) & 
                     (df_test['Date'] == date_obj)]
    if df_sub.empty:
        return "Observation not found", "", go.Figure(), "No data", "No data", None, ""
        
    baseline_inst = df_sub.copy()
    actual_demand = float(baseline_inst['Units_Sold'].iloc[0])

    changes = {}
    is_scenario = False
    if promo_val != 'base':
        changes['Promotion_Flag'] = promo_val
        is_scenario = True
    if price_pct != 0:
        changes['Unit_Price'] = baseline_inst['Unit_Price'].iloc[0] * (1 + price_pct / 100.0)
        is_scenario = True
    if cost_pct != 0:
        changes['Unit_Cost'] = baseline_inst['Unit_Cost'].iloc[0] * (1 + cost_pct / 100.0)
        is_scenario = True
    if inv_pct != 0:
        changes['Lag_1_Inventory_Level'] = baseline_inst['Lag_1_Inventory_Level'].iloc[0] * (1 + inv_pct / 100.0)
        is_scenario = True

    sim_res = simulator.simulate(baseline_inst, changes)
    base_pred = sim_res['baseline_forecast']
    scen_pred = sim_res['scenario_forecast']
    
    inv = float(baseline_inst['Inventory_Level'].iloc[0])
    reorder = float(baseline_inst['Reorder_Point'].iloc[0])
    order_qty = float(baseline_inst['Order_Quantity'].iloc[0])
    recent_dem = float(baseline_inst['Rolling_7d_Mean_Units_Sold'].iloc[0])

    base_decision = decision_engine.evaluate(base_pred, inv, reorder, order_qty, recent_dem)
    scen_decision = decision_engine.evaluate(scen_pred, inv, reorder, order_qty, recent_dem)
    comp_decision = decision_engine.evaluate_scenario_comparison(base_decision, scen_decision)

    def format_severity(sev):
        color = "success" if sev == "LOW" else "warning" if sev == "MEDIUM" else "danger"
        return dbc.Badge(sev, color=color, className="ms-2")

    baseline_kpi = html.Div([
        html.H4(f"Forecast Demand: {base_pred:.1f} units"),
        html.P(f"Actual Demand (Reference Only): {actual_demand:.1f} units | Error: {base_pred - actual_demand:.1f}", className="text-muted"),
        html.Hr(),
        html.P([html.Strong("Inventory Level: "), f"{inv} units"]),
        html.P([html.Strong("Reorder Point: "), f"{reorder} units"]),
        html.H5(["State: ", base_decision['decision_state'], format_severity(base_decision['severity'])], className="mt-3")
    ])

    base_shap = sim_res['baseline_shap']
    plain_text = generate_plain_language_explanation(base_shap)
    contribs = base_shap['feature_contributions']
    
    shap_dict_str = json.dumps({c['feature']: c['shap_value'] for c in contribs})
    
    contribs_sorted = sorted(contribs, key=lambda x: abs(x['shap_value']), reverse=False)[-5:]
    
    fig = go.Figure(go.Bar(
        x=[c['shap_value'] for c in contribs_sorted],
        y=[c['feature'] for c in contribs_sorted],
        orientation='h',
        marker_color=['red' if c['shap_value'] > 0 else 'blue' for c in contribs_sorted]
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=30, b=0),
        height=250,
        xaxis_title="Contribution to Forecast (Units)",
        title="Top Feature Contributions (SHAP)"
    )

    diff_val = sim_res['forecast_difference']
    diff_pct = sim_res['percentage_difference']
    diff_str = f"{diff_val:+.1f} units ({diff_pct:+.1f}%)" if diff_pct else f"{diff_val:+.1f} units"
    diff_color = "text-danger" if diff_val > 0 else "text-success"
    
    top_diff = sim_res['change_contributors'][0]
    
    scenario_desc = f"{top_diff['feature']} perturbed" if is_scenario else "None"
    
    scenario_kpi = html.Div([
        html.H4(f"Scenario Forecast: {scen_pred:.1f} units"),
        html.H5(["Difference: ", html.Span(diff_str, className=diff_color)]),
        html.Hr(),
        html.P(f"Under the model, this hypothetical change produces an estimated forecast change of {diff_val:+.1f} units."),
        html.P(f"Main driver of change: {top_diff['feature']} ({top_diff['contribution_diff']:+.1f})"),
        html.Hr(),
        html.H5(["Scenario State: ", scen_decision['decision_state'], format_severity(scen_decision['severity'])])
    ])

    decision_content = html.Div([
        html.H5("Triggered Rules:"),
        html.Ul([html.Li(f"✓ {r}", className="text-danger") for r in comp_decision['triggered_rules']] if comp_decision['triggered_rules'] else [html.Li("None", className="text-success")]),
        html.Hr(),
        html.H5("Explanation:"),
        html.P(comp_decision['scenario_decision']['explanation'])
    ])

    human_summary = html.Div([
        html.Strong("System decision: "), html.Span(comp_decision['scenario_decision']['decision_state']), html.Br(),
        html.Strong("Severity: "), html.Span(comp_decision['scenario_decision']['severity'])
    ])

    system_state_dict = {
        'SKU_ID': sku,
        'Warehouse_ID': warehouse,
        'Date': date_str,
        'baseline_forecast': float(base_pred),
        'actual_units_sold': float(actual_demand),
        'inventory_level': inv,
        'reorder_point': reorder,
        'baseline_decision_state': base_decision['decision_state'],
        'baseline_severity': base_decision['severity'],
        'scenario_applied': is_scenario,
        'scenario_description': scenario_desc,
        'scenario_forecast': float(scen_pred),
        'scenario_decision_state': comp_decision['scenario_decision']['decision_state'],
        'scenario_severity': comp_decision['scenario_decision']['severity'],
        'top_shap_drivers': shap_dict_str
    }

    return baseline_kpi, plain_text, fig, scenario_kpi, decision_content, system_state_dict, human_summary

def register_callbacks(app):

    @app.callback(
        Output('collection-monitor-content', 'children'),
        Input('btn-submit', 'n_clicks'),
        Input('filter-promo', 'value')
    )
    def update_monitor(n_clicks, promo_filter):
        stats = AuditLogger.get_collection_stats()
        return html.Div([
            html.P([html.Strong("Total Decisions Collected: "), str(stats['total'])]),
            html.P([html.Strong("ACCEPT: "), str(stats['ACCEPT'])]),
            html.P([html.Strong("REJECT: "), str(stats['REJECT'])]),
            html.P([html.Strong("OVERRIDE: "), str(stats['OVERRIDE'])]),
            html.Hr(),
            html.P("Diversity Coverage:"),
            html.Ul([
                html.Li(f"Unique SKUs: {stats.get('unique_skus_count', 0)}"),
                html.Li(f"Unique Warehouses: {stats.get('unique_whs_count', 0)}"),
                html.Li(f"Decision States: {', '.join(stats.get('decision_states', []))}")
            ])
        ])

    @app.callback(
        Output('warehouse-dropdown', 'options'),
        Output('warehouse-dropdown', 'value'),
        Output('sku-dropdown', 'options'),
        Output('sku-dropdown', 'value'),
        Output('date-dropdown', 'options'),
        Output('date-dropdown', 'value'),
        Input('filter-promo', 'value'),
        Input('warehouse-dropdown', 'value'),
        Input('sku-dropdown', 'value'),
        State('date-dropdown', 'value')
    )
    def update_diversity_filters_callback(promo_filter, selected_wh, selected_sku, selected_date):
        return update_diversity_filters(promo_filter, selected_wh, selected_sku, selected_date)

    @app.callback(
        Output('baseline-kpi-content', 'children'),
        Output('shap-explanation-text', 'children'),
        Output('shap-bar-chart', 'figure'),
        Output('scenario-kpi-content', 'children'),
        Output('decision-explanation-content', 'children'),
        Output('system-state-store', 'data'),
        Output('human-decision-summary', 'children'),
        Input('warehouse-dropdown', 'value'),
        Input('sku-dropdown', 'value'),
        Input('date-dropdown', 'value'),
        Input('scenario-promo', 'value'),
        Input('scenario-price-pct', 'value'),
        Input('scenario-cost-pct', 'value'),
        Input('scenario-inv-pct', 'value'),
        prevent_initial_call=False
    )
    def update_dashboard_callback(warehouse, sku, date_str, promo_val, price_pct, cost_pct, inv_pct):
        return update_dashboard(warehouse, sku, date_str, promo_val, price_pct, cost_pct, inv_pct)

    @app.callback(
        Output('override-panel', 'style'),
        Output('selected-action-store', 'data'),
        Output('btn-accept', 'outline'),
        Output('btn-reject', 'outline'),
        Output('btn-override', 'outline'),
        Input('btn-accept', 'n_clicks'),
        Input('btn-reject', 'n_clicks'),
        Input('btn-override', 'n_clicks'),
        prevent_initial_call=True
    )
    def handle_action_buttons(btn_a, btn_r, btn_o):
        triggered_id = ctx.triggered_id
        if not triggered_id:
            return {"display": "none"}, None, False, False, False
            
        action = None
        show_override = {"display": "none"}
        a_outline, r_outline, o_outline = True, True, True
        
        if triggered_id == 'btn-accept':
            action = 'ACCEPT'
            a_outline = False
        elif triggered_id == 'btn-reject':
            action = 'REJECT'
            r_outline = False
        elif triggered_id == 'btn-override':
            action = 'OVERRIDE'
            o_outline = False
            show_override = {"display": "block"}
            
        return show_override, action, a_outline, r_outline, o_outline

    @app.callback(
        Output('submit-message', 'children'),
        Output('last-submitted-fingerprint', 'data'),
        Input('btn-submit', 'n_clicks'),
        State('selected-action-store', 'data'),
        State('system-state-store', 'data'),
        State('override-reason', 'value'),
        State('override-note', 'value'),
        State('evaluator-id-input', 'value'),
        prevent_initial_call=True
    )
    def submit_decision_callback(n_clicks, action, system_state, reason, note, evaluator_id):
        msg = submit_decision(n_clicks, action, system_state, reason, note, evaluator_id)
        # If success, update the fingerprint
        if getattr(msg, 'color', None) == 'success':
            raw = {'sys': system_state, 'act': action, 'rsn': reason, 'nt': note, 'evl': evaluator_id}
            fp = hashlib.md5(json.dumps(raw, sort_keys=True).encode()).hexdigest()
            return msg, fp
        return msg, no_update

    @app.callback(
        Output('btn-submit', 'disabled'),
        Input('last-submitted-fingerprint', 'data'),
        Input('system-state-store', 'data'),
        Input('selected-action-store', 'data'),
        Input('override-reason', 'value'),
        Input('override-note', 'value'),
        Input('evaluator-id-input', 'value')
    )
    def update_submit_button_state(last_fp, system_state, action, reason, note, evaluator_id):
        if not last_fp:
            return False
        raw = {'sys': system_state, 'act': action, 'rsn': reason, 'nt': note, 'evl': evaluator_id}
        curr_fp = hashlib.md5(json.dumps(raw, sort_keys=True).encode()).hexdigest()
        return curr_fp == last_fp

    @app.callback(
        Output('evaluator-id-display', 'children'),
        Input('evaluator-id-input', 'value')
    )
    def update_evaluator_id_display(val):
        if val and str(val).strip():
            return f"Evaluator: {str(val).strip()}"
        return ""

    @app.callback(
        Output('feedback-message', 'children'),
        Input('btn-submit-feedback', 'n_clicks'),
        State('system-state-store', 'data'),
        State('feedback-type', 'value'),
        State('feedback-text', 'value'),
        State('evaluator-id-input', 'value'),
        prevent_initial_call=True
    )
    def submit_feedback_callback(n_clicks, system_state, f_type, f_text, evaluator_id):
        return submit_feedback(n_clicks, system_state, f_type, f_text, evaluator_id)
