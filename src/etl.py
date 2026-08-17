import pandas as pd
import numpy as np
import logging
import sys

# Configure logging for validation warnings
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def run_etl(input_path: str = 'data/supply_chain_dataset1.csv', output_path: str = 'data/processed_dataset.csv') -> pd.DataFrame:
    """
    Phase I ETL Pipeline for AdaptiveXSC.
    Validates, transforms, and outputs the dataset without modifying the raw source.
    """
    logging.info(f"Starting ETL. Reading raw data from {input_path}...")
    try:
        df = pd.read_csv(input_path)
    except FileNotFoundError:
        logging.error(f"Input file {input_path} not found.")
        sys.exit(1)
        
    initial_rows, initial_cols = df.shape
    logging.info(f"Loaded {initial_rows} rows and {initial_cols} columns.")
    
    # --- VALIDATION ---
    # 1. Required columns
    expected_cols = [
        'Date', 'SKU_ID', 'Warehouse_ID', 'Supplier_ID', 'Region', 
        'Units_Sold', 'Inventory_Level', 'Supplier_Lead_Time_Days', 
        'Reorder_Point', 'Order_Quantity', 'Unit_Cost', 'Unit_Price', 
        'Promotion_Flag', 'Stockout_Flag', 'Demand_Forecast'
    ]
    missing_cols = [c for c in expected_cols if c not in df.columns]
    if missing_cols:
        logging.error(f"Missing required columns: {missing_cols}")
        
    # 2. Missing values
    missing_counts = df.isnull().sum()
    if missing_counts.sum() > 0:
        logging.warning(f"Missing values found:\n{missing_counts[missing_counts > 0]}")
        
    # 3. Duplicate rows
    duplicates = df.duplicated().sum()
    if duplicates > 0:
        logging.warning(f"Found {duplicates} duplicate rows. Kept as is per Phase I bounds.")
        
    # 4. Negative checks
    numeric_cols = ['Units_Sold', 'Inventory_Level', 'Order_Quantity', 'Unit_Cost', 'Unit_Price']
    for col in numeric_cols:
        if col in df.columns and (df[col] < 0).any():
            logging.warning(f"Negative values found in {col}!")
            
    # 5. Zero-variance checks (Specifically noting Stockout_Flag limitation)
    for col in df.columns:
        if df[col].nunique() <= 1:
            logging.warning(f"Zero-variance column detected: '{col}'. Limitation documented, no synthetic data generated.")
            
    # --- TRANSFORMATIONS ---
    # 1. Date parsing
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    if df['Date'].isnull().any():
        logging.warning("Some dates could not be parsed and are now NaT.")
        
    # 2. Categorical conversion
    cat_cols = ['SKU_ID', 'Warehouse_ID', 'Supplier_ID', 'Region']
    for col in cat_cols:
        if col in df.columns:
            df[col] = df[col].astype('category')
            
    # 3. Temporal feature preparation
    df['Year'] = df['Date'].dt.year
    df['Month'] = df['Date'].dt.month
    df['DayOfWeek'] = df['Date'].dt.dayofweek
    
    # 4. Chronological sorting
    df = df.sort_values(by=['Warehouse_ID', 'SKU_ID', 'Date']).reset_index(drop=True)
    
    # --- OUTPUT ---
    final_rows, final_cols = df.shape
    logging.info(f"ETL completed. Final shape: {final_rows} rows, {final_cols} columns.")
    
    if output_path:
        df.to_csv(output_path, index=False)
        logging.info(f"Saved processed dataset to {output_path}")
        
    return df

if __name__ == "__main__":
    run_etl()
