import unittest
import tempfile
import os
import csv
from pydantic import ValidationError
from src.audit.schema import AuditRecord
from src.audit.logger import AuditLogger

class TestAuditLogger(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.audit_file = os.path.join(self.temp_dir.name, 'test_audit.csv')
        self.logger = AuditLogger(filepath=self.audit_file)
        
        self.valid_base_data = {
            'SKU_ID': 'TEST_SKU',
            'Warehouse_ID': 'WH_TEST',
            'Date': '2024-12-01',
            'baseline_forecast': 10.5,
            'inventory_level': 20.0,
            'reorder_point': 15.0,
            'baseline_decision_state': 'NORMAL',
            'baseline_severity': 'LOW',
            'scenario_applied': False,
            'scenario_description': 'None',
            'scenario_forecast': 10.5,
            'scenario_decision_state': 'NORMAL',
            'scenario_severity': 'LOW',
            'top_shap_drivers': '{"Lag_1": 1.2}',
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_accept_creates_record(self): # 1
        data = {**self.valid_base_data, 'manager_action': 'ACCEPT'}
        record = AuditRecord(**data)
        self.logger.log_decision(record)
        with open(self.audit_file, 'r') as f:
            rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['manager_action'], 'ACCEPT')

    def test_reject_creates_record(self): # 2
        data = {**self.valid_base_data, 'manager_action': 'REJECT'}
        record = AuditRecord(**data)
        self.logger.log_decision(record)
        with open(self.audit_file, 'r') as f:
            self.assertEqual(len(list(csv.DictReader(f))), 1)

    def test_override_creates_record(self): # 3
        data = {**self.valid_base_data, 'manager_action': 'OVERRIDE', 'override_reason': 'Supplier Delay'}
        record = AuditRecord(**data)
        self.logger.log_decision(record)
        with open(self.audit_file, 'r') as f:
            rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['override_reason'], 'Supplier Delay')

    def test_override_without_reason_rejected(self): # 4
        data = {**self.valid_base_data, 'manager_action': 'OVERRIDE'}
        with self.assertRaises(ValidationError):
            AuditRecord(**data)

    def test_missing_manager_action_rejected(self): # 5
        data = {**self.valid_base_data}
        with self.assertRaises(ValidationError):
            AuditRecord(**data)
            
    def test_invalid_manager_action_rejected(self):
        data = {**self.valid_base_data, 'manager_action': 'INVALID_ACTION'}
        with self.assertRaises(ValidationError):
            AuditRecord(**data)

    def test_unique_audit_ids(self): # 6 & 7
        data1 = {**self.valid_base_data, 'manager_action': 'ACCEPT'}
        data2 = {**self.valid_base_data, 'manager_action': 'REJECT'}
        id1 = self.logger.log_decision(AuditRecord(**data1))
        id2 = self.logger.log_decision(AuditRecord(**data2))
        
        self.assertNotEqual(id1, id2)
        with open(self.audit_file, 'r') as f:
            rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]['audit_id'], id1)
            self.assertEqual(rows[1]['audit_id'], id2)

    def test_system_state_preserved(self): # 8, 9, 10
        data = {**self.valid_base_data, 'manager_action': 'OVERRIDE', 'override_reason': 'Other'}
        self.logger.log_decision(AuditRecord(**data))
        with open(self.audit_file, 'r') as f:
            row = list(csv.DictReader(f))[0]
            self.assertEqual(float(row['baseline_forecast']), 10.5)
            self.assertEqual(row['baseline_decision_state'], 'NORMAL')
            self.assertEqual(row['manager_action'], 'OVERRIDE')
            
    def test_override_note(self): # 11, 12
        data = {**self.valid_base_data, 'manager_action': 'OVERRIDE', 'override_reason': 'Other', 'override_note': 'Test note'}
        self.logger.log_decision(AuditRecord(**data))
        with open(self.audit_file, 'r') as f:
            row = list(csv.DictReader(f))[0]
            self.assertEqual(row['override_note'], 'Test note')

    def test_structured_fields_serialize(self): # 13
        data = {**self.valid_base_data, 'manager_action': 'ACCEPT'}
        self.logger.log_decision(AuditRecord(**data))
        with open(self.audit_file, 'r') as f:
            row = list(csv.DictReader(f))[0]
            self.assertEqual(row['top_shap_drivers'], '{"Lag_1": 1.2}')
            
    def test_append_only(self): # 14
        data1 = {**self.valid_base_data, 'manager_action': 'ACCEPT'}
        self.logger.log_decision(AuditRecord(**data1))
        
        with open(self.audit_file, 'r') as f:
            self.assertEqual(len(list(csv.DictReader(f))), 1)
            
        data2 = {**self.valid_base_data, 'manager_action': 'REJECT'}
        self.logger.log_decision(AuditRecord(**data2))
        
        with open(self.audit_file, 'r') as f:
            self.assertEqual(len(list(csv.DictReader(f))), 2)

if __name__ == '__main__':
    unittest.main()
