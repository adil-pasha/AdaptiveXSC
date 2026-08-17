import pandas as pd
from src.app.callbacks import update_diversity_filters

def run_tests():
    # Test 1: Promotion Filter == 1
    wh, s_wh, sku, s_sku, dt, s_dt = update_diversity_filters(1, 'WH_1', 'SKU_1', '2024-12-01')
    print("Filter Promo=1 -> Warehouses count:", len(wh))
    
    # Test 2: Promotion Filter == 0
    wh, s_wh, sku, s_sku, dt, s_dt = update_diversity_filters(0, 'WH_1', 'SKU_1', '2024-12-01')
    print("Filter Promo=0 -> Warehouses count:", len(wh))
    
    # Test 3: Stale selection reset
    # Pass an invalid warehouse that is definitely not in the dataset
    wh, s_wh, sku, s_sku, dt, s_dt = update_diversity_filters('any', 'INVALID_WH', 'SKU_1', '2024-12-01')
    print("Invalid WH input -> Reset to:", s_wh)
    assert s_wh != 'INVALID_WH'
    
if __name__ == '__main__':
    run_tests()
    print("Filter tests passed!")
