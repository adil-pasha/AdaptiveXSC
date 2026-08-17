from src.app.callbacks import submit_decision, update_dashboard, audit_logger
from src.audit.logger import AuditLogger
import csv

def run_e2e_test():
    # Setup test logger to prevent polluting production data
    import os
    test_log_path = 'data/test_decision_audit_log.csv'
    if os.path.exists(test_log_path):
        os.remove(test_log_path)
    
    # Overwrite the global logger instance for this run
    global audit_logger
    audit_logger.filepath = test_log_path
    audit_logger._ensure_file_exists()
    
    # 1. Select valid observation (WH_3, SKU_25, 2024-12-21)
    wh = "WH_3"
    sku = "SKU_25"
    date_str = "2024-12-21"
    
    # 2 & 3 & 4 & 5. Apply scenario (+10% price, -5% cost) and get system state
    _, _, _, _, _, system_state_dict, _, _ = update_dashboard(wh, sku, date_str, 'base', 10, -5, 0)
    
    print("Baseline Forecast:", system_state_dict['baseline_forecast'])
    print("Baseline Decision:", system_state_dict['baseline_decision_state'])
    print("Scenario Forecast:", system_state_dict['scenario_forecast'])
    print("Scenario Decision:", system_state_dict['scenario_decision_state'])
    
    # 6 & 7 & 8 & 9. Manager chooses OVERRIDE, "Supplier Delay", adds note, submits
    print("Submitting OVERRIDE decision...")
    result_alert = submit_decision(
        n_clicks=1, 
        action='OVERRIDE', 
        system_state=system_state_dict, 
        reason='Supplier Delay', 
        note='Test note'
    )
    
    # 10 & 11. Confirm success and capture audit_id
    print("Alert Output:", getattr(result_alert, 'children', result_alert))
    
    # Extract ID
    audit_id = result_alert.children.split('Audit ID: ')[1]
    print(f"Captured Audit ID: {audit_id}")
    
    # 12 & 13 & 14. Read newly appended row and compare
    with open(test_log_path, 'r') as f:
        reader = list(csv.DictReader(f))
        last_row = reader[-1]

        
    print(f"\nVerifying stored record matches system state exactly...")
    assert last_row['audit_id'] == audit_id
    assert float(last_row['baseline_forecast']) == system_state_dict['baseline_forecast']
    assert last_row['baseline_decision_state'] == system_state_dict['baseline_decision_state']
    assert float(last_row['scenario_forecast']) == system_state_dict['scenario_forecast']
    assert last_row['scenario_decision_state'] == system_state_dict['scenario_decision_state']
    assert last_row['manager_action'] == 'OVERRIDE'
    assert last_row['override_reason'] == 'Supplier Delay'
    assert last_row['override_note'] == 'Test note'
    
    print("ALL MATCHES CONFIRMED. SYSTEM STATE IS SEPARATE FROM HUMAN DECISION.")

if __name__ == '__main__':
    run_e2e_test()
