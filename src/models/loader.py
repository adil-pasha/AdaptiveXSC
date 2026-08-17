import pandas as pd
import xgboost as xgb
import warnings
warnings.filterwarnings('ignore')

class DataLoader:
    _instance = None
    _df_test = None
    _model = None

    @classmethod
    def load(cls):
        if cls._df_test is None or cls._model is None:
            # Load Data
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

            cutoff = pd.to_datetime('2024-10-19')
            test_mask = df_model['Date'] >= cutoff
            cls._df_test = df_model[test_mask].copy()

            # Load Model
            cls._model = xgb.XGBRegressor()
            cls._model.load_model('models/v3_tuned.json')

        return cls._model, cls._df_test
