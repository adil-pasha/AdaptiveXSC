import os
import pandas as pd
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

def train_and_save_model():
    print("Loading and preparing data...")
    df = pd.read_csv('data/processed_dataset.csv')
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values(by=['Warehouse_ID', 'SKU_ID', 'Date']).reset_index(drop=True)
    grouped = df.groupby(['Warehouse_ID', 'SKU_ID'])

    df['Lag_1_Inventory_Level'] = grouped['Inventory_Level'].shift(1)
    df['Lag_1_Order_Quantity'] = grouped['Order_Quantity'].shift(1)
    df['Lag_1_Units_Sold'] = grouped['Units_Sold'].shift(1)
    df['Lag_7_Units_Sold'] = grouped['Units_Sold'].shift(7)
    df['Rolling_7d_Mean_Units_Sold'] = grouped['Units_Sold'].transform(lambda s: s.shift(1).rolling(7, min_periods=7).mean())

    features_non_null = ['Lag_1_Inventory_Level', 'Lag_1_Order_Quantity', 'Lag_1_Units_Sold', 'Lag_7_Units_Sold', 'Rolling_7d_Mean_Units_Sold']
    df_model = df.dropna(subset=features_non_null).copy()

    target = 'Units_Sold'
    features = [
        'Lag_1_Units_Sold', 'Lag_7_Units_Sold', 'Rolling_7d_Mean_Units_Sold',
        'Lag_1_Inventory_Level', 'Lag_1_Order_Quantity',
        'Unit_Cost', 'Unit_Price', 'Promotion_Flag'
    ]

    cutoff = pd.to_datetime('2024-10-19')
    train_mask = df_model['Date'] < cutoff
    df_train = df_model[train_mask].copy()

    v3_params = {
        'colsample_bytree': 0.8, 'subsample': 1.0, 'max_depth': 3, 
        'min_child_weight': 1, 'learning_rate': 0.1, 'n_estimators': 200, 
        'random_state': 42, 'tree_method': 'hist'
    }
    
    print("Training V3_Tuned...")
    model = xgb.XGBRegressor(**v3_params)
    model.fit(df_train[features], df_train[target])

    os.makedirs('models', exist_ok=True)
    model_path = 'models/v3_tuned.json'
    model.save_model(model_path)
    print(f"Model saved to {model_path}")

if __name__ == '__main__':
    train_and_save_model()
