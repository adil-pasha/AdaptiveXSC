import pandas as pd
import numpy as np
import time
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def wape(y_true, y_pred):
    """Weighted Absolute Percentage Error."""
    return np.sum(np.abs(y_true - y_pred)) / np.sum(np.abs(y_true))

def create_features(df):
    logging.info("Starting feature engineering...")
    df = df.copy()
    
    # Sort chronologically by panel
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values(by=['Warehouse_ID', 'SKU_ID', 'Date']).reset_index(drop=True)
    
    # Group by for panel operations
    grouped = df.groupby(['Warehouse_ID', 'SKU_ID'])
    
    # Lag state features (Conservative assumption: available before today's demand)
    df['Lag_1_Inventory_Level'] = grouped['Inventory_Level'].shift(1)
    df['Lag_1_Order_Quantity'] = grouped['Order_Quantity'].shift(1)
    
    # Lag target features
    df['Lag_1_Units_Sold'] = grouped['Units_Sold'].shift(1)
    df['Lag_7_Units_Sold'] = grouped['Units_Sold'].shift(7)
    
    # Rolling features (shift by 1 to exclude today)
    df['Rolling_7d_Mean_Units_Sold'] = grouped['Units_Sold'].transform(
        lambda s: s.shift(1).rolling(window=7, min_periods=7).mean()
    )
    
    # Ensure categorical dtypes for XGBoost
    cat_cols = ['SKU_ID', 'Warehouse_ID', 'Supplier_ID', 'Region']
    for col in cat_cols:
        df[col] = df[col].astype('category')
        
    return df

def run_experiment():
    df = pd.read_csv('data/processed_dataset.csv')
    df = create_features(df)
    
    # Drop missing rows created by lags
    features_requiring_non_null = [
        'Lag_1_Inventory_Level', 'Lag_1_Order_Quantity', 
        'Lag_1_Units_Sold', 'Lag_7_Units_Sold', 'Rolling_7d_Mean_Units_Sold'
    ]
    df_model = df.dropna(subset=features_requiring_non_null).copy()
    
    target = 'Units_Sold'
    
    # Chronological Split
    cutoff_date = pd.to_datetime('2024-10-19')
    train_mask = df_model['Date'] < cutoff_date
    test_mask = df_model['Date'] >= cutoff_date
    
    df_train = df_model[train_mask].copy()
    df_test = df_model[test_mask].copy()
    
    y_train = df_train[target]
    y_test = df_test[target]
    
    # ---------------------------------------------------------
    # Define Feature Sets for Phase II-A.2
    # ---------------------------------------------------------
    features_v1 = [
        'SKU_ID', 'Warehouse_ID', 'Supplier_ID', 'Region',
        'Year', 'Month', 'DayOfWeek',
        'Unit_Cost', 'Unit_Price', 'Promotion_Flag',
        'Lag_1_Inventory_Level', 'Lag_1_Order_Quantity',
        'Lag_1_Units_Sold', 'Lag_7_Units_Sold', 'Rolling_7d_Mean_Units_Sold'
    ]
    
    features_v2a = [
        'Lag_1_Units_Sold', 'Lag_7_Units_Sold', 'Rolling_7d_Mean_Units_Sold',
        'Lag_1_Inventory_Level', 'Lag_1_Order_Quantity'
    ]
    
    features_v2b = features_v2a + [
        'Unit_Cost', 'Unit_Price', 'Promotion_Flag'
    ]
    
    def evaluate(y_t, y_p):
        return {
            'MAE': mean_absolute_error(y_t, y_p),
            'RMSE': np.sqrt(mean_squared_error(y_t, y_p)),
            'WAPE': wape(y_t, y_p)
        }
        
    results = {}
    
    configs = {
        'baseline_xgboost_v1': features_v1,
        'Model_V2-A (Lag+State)': features_v2a,
        'Model_V2-B (Lag+State+Operational)': features_v2b
    }
    
    for model_name, feats in configs.items():
        logging.info(f"Training {model_name}...")
        start_train = time.time()
        
        model = xgb.XGBRegressor(
            n_estimators=100, 
            max_depth=5, 
            random_state=42, 
            enable_categorical=True,
            tree_method='hist'
        )
        model.fit(df_train[feats], y_train)
        
        train_time = time.time() - start_train
        
        start_infer = time.time()
        preds = model.predict(df_test[feats])
        infer_time = time.time() - start_infer
        
        res = evaluate(y_test, preds)
        res['Train_Time_s'] = train_time
        res['Infer_Time_s'] = infer_time
        results[model_name] = res

    # Baselines
    results['Naive Baseline (Lag-1)'] = evaluate(y_test, df_test['Lag_1_Units_Sold'])
    results['Naive Baseline (Seasonal Lag-7)'] = evaluate(y_test, df_test['Lag_7_Units_Sold'])
    results['External Reference (Demand_Forecast)'] = evaluate(y_test, df_test['Demand_Forecast'])
    
    print("\n" + "="*50)
    print("PHASE II-A.2 EXPERIMENT RESULTS")
    print("="*50)
    for name, r in results.items():
        print(f"\n--- {name} ---")
        for k, v in r.items():
            print(f"{k}: {v:.4f}")
            
if __name__ == '__main__':
    run_experiment()
