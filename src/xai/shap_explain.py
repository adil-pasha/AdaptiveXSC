import numpy as np
import pandas as pd
import shap
import xgboost as xgb

class SHAPExplainer:
    def __init__(self, model):
        """
        Initialize the SHAP explainer with a frozen model.
        Args:
            model: An xgboost.XGBRegressor or booster.
        """
        self.model = model
        self.explainer = shap.TreeExplainer(self.model)

    def get_global_importance(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Generate a global SHAP importance ranking.
        Args:
            X: The feature matrix.
        Returns:
            DataFrame with columns ['feature', 'mean_abs_shap', 'rank']
        """
        shap_values = self.explainer(X)
        vals = np.abs(shap_values.values).mean(0)
        feature_names = X.columns
        
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'mean_abs_shap': vals
        })
        importance_df = importance_df.sort_values(by='mean_abs_shap', ascending=False).reset_index(drop=True)
        importance_df['rank'] = importance_df.index + 1
        
        return importance_df

    def get_local_explanation(self, x_instance: pd.DataFrame, actual_value: float = None) -> dict:
        """
        Generate a local explanation for a single prediction.
        Args:
            x_instance: A DataFrame containing exactly 1 row (the feature matrix).
            actual_value: The actual Units_Sold (if available).
        Returns:
            dict containing structured explanation data.
        """
        feature_cols = self.model.feature_names_in_
        x_features = x_instance[feature_cols]
        shap_val_obj = self.explainer(x_features)
        shap_values = shap_val_obj.values[0]
        base_value = shap_val_obj.base_values[0]
        feature_names = x_features.columns.tolist()
        feature_values = x_features.iloc[0].tolist()
        
        prediction = base_value + np.sum(shap_values)
        
        contributions = []
        for i in range(len(feature_names)):
            contributions.append({
                'feature': feature_names[i],
                'value': feature_values[i],
                'shap_value': float(shap_values[i])
            })
            
        contributions = sorted(contributions, key=lambda k: abs(k['shap_value']), reverse=True)
        
        positive_contributors = [c for c in contributions if c['shap_value'] > 0]
        negative_contributors = [c for c in contributions if c['shap_value'] < 0]
        
        explanation = {
            'actual_Units_Sold': actual_value,
            'predicted_Units_Sold': float(prediction),
            'prediction_error': float(actual_value - prediction) if actual_value is not None else None,
            'base_value': float(base_value),
            'feature_contributions': contributions,
            'top_positive_contributors': positive_contributors[:3],
            'top_negative_contributors': negative_contributors[:3]
        }
        
        # Verify numerical tolerance
        reconstructed = base_value + sum([c['shap_value'] for c in contributions])
        explanation['reconstruction_verified'] = abs(reconstructed - prediction) < 1e-4
        
        return explanation

def generate_plain_language_explanation(local_expl_data: dict) -> str:
    """
    Convert a local SHAP explanation into a concise human-readable explanation.
    """
    pred = round(local_expl_data['predicted_Units_Sold'], 1)
    
    # Filter features that have a meaningful magnitude (e.g., > 0.1 units)
    pos_contributors = [c for c in local_expl_data['top_positive_contributors'] if c['shap_value'] > 0.1]
    neg_contributors = [c for c in local_expl_data['top_negative_contributors'] if c['shap_value'] < -0.1]
    
    def map_feature_name(f):
        if f == 'Rolling_7d_Mean_Units_Sold': return "recent 7-day demand"
        if f == 'Promotion_Flag': return "active promotion status"
        if f == 'Lag_1_Units_Sold': return "previous-day demand"
        if f == 'Lag_7_Units_Sold': return "demand 7 days ago"
        if f == 'Lag_1_Inventory_Level': return "previous-day inventory level"
        if f == 'Lag_1_Order_Quantity': return "previous-day order quantity"
        if f == 'Unit_Price': return "unit price"
        if f == 'Unit_Cost': return "unit cost"
        return f.replace("_", " ")

    explanation = f"Forecast demand is {pred} units."
    
    for c in pos_contributors[:2]:
        name = map_feature_name(c['feature'])
        val = round(c['shap_value'], 2)
        explanation += f" The {name} contributed approximately +{val} units to the forecast."
        
    for c in neg_contributors[:2]:
        name = map_feature_name(c['feature'])
        val = round(abs(c['shap_value']), 2)
        explanation += f" The {name} decreased the model prediction by approximately {val} units."
        
    return explanation
