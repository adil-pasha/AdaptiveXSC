import pandas as pd
import numpy as np
from src.xai.shap_explain import SHAPExplainer

ALLOWED_SCENARIO_VARS = {
    'Lag_1_Units_Sold',
    'Lag_7_Units_Sold',
    'Rolling_7d_Mean_Units_Sold',
    'Lag_1_Inventory_Level',
    'Lag_1_Order_Quantity',
    'Unit_Cost',
    'Unit_Price',
    'Promotion_Flag'
}

class WhatIfSimulator:
    def __init__(self, model):
        """
        Initialize the what-if simulator with a frozen model.
        """
        self.model = model
        self.explainer = SHAPExplainer(self.model)
        
    def simulate(self, baseline_instance: pd.DataFrame, changes: dict) -> dict:
        """
        Run a what-if scenario.
        
        Args:
            baseline_instance: DataFrame with 1 row containing the valid baseline observation.
            changes: Dictionary of controlled input changes.
            
        Returns:
            Dictionary with baseline/scenario predictions, features, and SHAP explanations.
        """
        # Validate changes
        for k in changes.keys():
            if k in ['Units_Sold', 'Demand_Forecast', 'Stockout_Flag']:
                raise ValueError(f"Modifying '{k}' is strictly prohibited.")
            if k not in ALLOWED_SCENARIO_VARS:
                raise ValueError(f"Feature '{k}' is not allowed for scenario perturbation.")
                
        scenario_instance = baseline_instance.copy()
        
        # Apply changes with basic validation
        for k, v in changes.items():
            if k == 'Promotion_Flag':
                if v not in [0, 1]:
                    raise ValueError("Promotion_Flag must be 0 or 1.")
                scenario_instance[k] = float(v)
            elif k in ['Unit_Price', 'Unit_Cost']:
                if v < 0:
                    raise ValueError(f"{k} cannot be negative.")
                scenario_instance[k] = float(v)
            elif k in ['Lag_1_Units_Sold', 'Lag_7_Units_Sold', 'Rolling_7d_Mean_Units_Sold', 'Lag_1_Inventory_Level', 'Lag_1_Order_Quantity']:
                if v < 0:
                    raise ValueError(f"{k} cannot be negative.")
                scenario_instance[k] = float(v)
                
        # Generate explanations (which include the base/scenario predictions)
        base_exp = self.explainer.get_local_explanation(baseline_instance)
        scen_exp = self.explainer.get_local_explanation(scenario_instance)
        
        base_pred = base_exp['predicted_Units_Sold']
        scen_pred = scen_exp['predicted_Units_Sold']
        diff = scen_pred - base_pred
        
        if base_pred != 0:
            pct_diff = (diff / base_pred) * 100
        else:
            pct_diff = None
            
        # Calculate SHAP differences (contributors to forecast change)
        base_contrib = {c['feature']: c['shap_value'] for c in base_exp['feature_contributions']}
        scen_contrib = {c['feature']: c['shap_value'] for c in scen_exp['feature_contributions']}
        
        change_contributors = []
        for f in ALLOWED_SCENARIO_VARS:
            c_diff = scen_contrib.get(f, 0) - base_contrib.get(f, 0)
            change_contributors.append({'feature': f, 'contribution_diff': c_diff})
            
        change_contributors = sorted(change_contributors, key=lambda x: abs(x['contribution_diff']), reverse=True)
        
        return {
            'baseline_features': baseline_instance.iloc[0].to_dict(),
            'scenario_features': scenario_instance.iloc[0].to_dict(),
            'baseline_forecast': base_pred,
            'scenario_forecast': scen_pred,
            'forecast_difference': diff,
            'percentage_difference': pct_diff,
            'baseline_shap': base_exp,
            'scenario_shap': scen_exp,
            'change_contributors': change_contributors
        }
