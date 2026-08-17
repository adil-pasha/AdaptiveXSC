import os
import sys

def run_healthcheck():
    print("Starting AdaptiveXSC Healthcheck...")
    errors = []
    
    # 1. Check datasets
    if not os.path.exists('data/supply_chain_dataset1.csv'):
        errors.append("Raw dataset not found: data/supply_chain_dataset1.csv")
    if not os.path.exists('data/processed_dataset.csv'):
        errors.append("Processed dataset not found: data/processed_dataset.csv")
        
    # 2. Check model artifact
    if not os.path.exists('models/v3_tuned.json'):
        errors.append("Model artifact not found: models/v3_tuned.json")
        
    # 3. Test model load (without triggering a Dash server)
    try:
        from src.models.loader import DataLoader
        print("Testing DataLoader...")
        model, df_test = DataLoader.load()
        if df_test is None or df_test.empty:
            errors.append("DataLoader returned empty dataframe.")
        if model is None:
            errors.append("DataLoader returned None for model.")
    except Exception as e:
        errors.append(f"Failed to load model/data: {str(e)}")
        
    # 4. Check Database connection via AuditLogger
    try:
        from src.audit.logger import AuditLogger
        print("Testing Database connection...")
        # Instantiating AuditLogger creates tables and migrates if needed
        logger = AuditLogger()
        stats = logger.get_collection_stats()
        if not isinstance(stats, dict) or 'total' not in stats:
            errors.append("Database stats check failed.")
    except Exception as e:
        errors.append(f"Failed database check: {str(e)}")
        
    if errors:
        print("\nHealthcheck FAILED with the following errors:")
        for err in errors:
            print(f" - {err}")
        sys.exit(1)
    
    print("\nHealthcheck PASSED. System is ready for deployment.")
    sys.exit(0)

if __name__ == '__main__':
    run_healthcheck()
