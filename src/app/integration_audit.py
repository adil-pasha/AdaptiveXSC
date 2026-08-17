import pandas as pd
import numpy as np
from src.models.loader import DataLoader
from src.sim.simulator import WhatIfSimulator
from src.sim.decision import DecisionEngine
from src.xai.shap_explain import generate_plain_language_explanation
from src.app.callbacks import update_dashboard
import json

def run_audit():
    model, df_test = DataLoader.load()
    simulator = WhatIfSimulator(model)
    decision_engine = DecisionEngine(high_demand_multiplier=1.5)

    # Pick 5 valid observations
    np.random.seed(42)
    sample_indices = np.random.choice(df_test.index, 5, replace=False)
    samples = df_test.loc[sample_indices].copy()

    results = []
    
    for _, row in samples.iterrows():
        wh = row['Warehouse_ID']
        sku = row['SKU_ID']
        date_obj = row['Date']
        date_str = date_obj.strftime('%Y-%m-%d')
        
        baseline_inst = df_test[(df_test['Warehouse_ID'] == wh) & 
                                (df_test['SKU_ID'] == sku) & 
                                (df_test['Date'] == date_obj)].copy()
        
        # --- DIRECT PYTHON LOGIC ---
        # 1. Forecast
        sim_res = simulator.simulate(baseline_inst, {})
        base_pred = sim_res['baseline_forecast']
        
        # 2. SHAP
        base_shap = sim_res['baseline_shap']
        direct_shap_text = generate_plain_language_explanation(base_shap)
        
        # 3. Scenario (Price +10%, Cost -5%)
        changes = {'Unit_Price': baseline_inst['Unit_Price'].iloc[0] * 1.10,
                   'Unit_Cost': baseline_inst['Unit_Cost'].iloc[0] * 0.95}
        sim_res_scenario = simulator.simulate(baseline_inst, changes)
        scen_pred = sim_res_scenario['scenario_forecast']
        diff_val = sim_res_scenario['forecast_difference']
        
        # 4. Decision
        inv = baseline_inst['Inventory_Level'].iloc[0]
        reorder = baseline_inst['Reorder_Point'].iloc[0]
        order_qty = baseline_inst['Order_Quantity'].iloc[0]
        recent_dem = baseline_inst['Rolling_7d_Mean_Units_Sold'].iloc[0]
        
        base_decision = decision_engine.evaluate(base_pred, inv, reorder, order_qty, recent_dem)
        scen_decision = decision_engine.evaluate(scen_pred, inv, reorder, order_qty, recent_dem)
        comp_decision = decision_engine.evaluate_scenario_comparison(base_decision, scen_decision)
        
        # --- DASHBOARD CALLBACK LOGIC ---
        # Baseline callback
        bkpi, stext, sfig, skpi, dcontent = update_dashboard(wh, sku, date_str, 'base', 0, 0, 0)
        
        # Scenario callback
        bkpi2, stext2, sfig2, skpi2, dcontent2 = update_dashboard(wh, sku, date_str, 'base', 10, -5, 0)
        
        results.append({
            'wh': wh,
            'sku': sku,
            'date': date_str,
            'direct_base_pred': float(base_pred),
            'dash_base_kpi_text': str(bkpi),
            'direct_shap_text': direct_shap_text,
            'dash_shap_text': str(stext),
            'direct_scen_pred': float(scen_pred),
            'dash_scen_kpi_text': str(skpi2),
            'direct_dec_state': comp_decision['scenario_decision']['decision_state'],
            'dash_dec_content': str(dcontent2)
        })

    with open('audit_results.json', 'w') as f:
        json.dump(results, f, indent=2)

if __name__ == '__main__':
    run_audit()
