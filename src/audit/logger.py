import os
import csv
import sqlite3
from contextlib import closing
from src.audit.schema import AuditRecord, FeedbackRecord

class AuditLogger:
    def __init__(self, filepath='data/decision_audit_log.db', csv_path='data/decision_audit_log.csv'):
        self.filepath = filepath
        self.csv_path = csv_path
        self._ensure_db_exists()
        self._migrate_from_csv_if_needed()

    def _ensure_db_exists(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with closing(sqlite3.connect(self.filepath)) as conn:
            with conn:
                cursor = conn.cursor()
                # Create audit_records table
                columns = [f"{h} TEXT PRIMARY KEY" if h == 'audit_id' else f"{h} TEXT" for h in AuditRecord.get_csv_headers()]
                cursor.execute(f"CREATE TABLE IF NOT EXISTS audit_records ({', '.join(columns)})")
                
                # Create feedback_records table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS feedback_records (
                        feedback_id TEXT PRIMARY KEY,
                        timestamp TEXT,
                        evaluator_id TEXT,
                        SKU_ID TEXT,
                        Warehouse_ID TEXT,
                        Date TEXT,
                        baseline_decision_state TEXT,
                        scenario_description TEXT,
                        feedback_type TEXT,
                        feedback_text TEXT
                    )
                """)

    def _migrate_from_csv_if_needed(self):
        """Migrate existing records from CSV to SQLite without destructing the CSV."""
        if not os.path.exists(self.csv_path):
            return
            
        with closing(sqlite3.connect(self.filepath)) as conn:
            with conn:
                cursor = conn.cursor()
                # Check if we already migrated
                cursor.execute("SELECT COUNT(*) FROM audit_records")
                if cursor.fetchone()[0] > 0:
                    return # Already has data, assume migrated
                    
                with open(self.csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    headers = AuditRecord.get_csv_headers()
                    
                    for row in reader:
                        # Pad missing columns with empty string
                        values = [row.get(h, '') for h in headers]
                        placeholders = ', '.join(['?'] * len(headers))
                        try:
                            cursor.execute(f"INSERT OR IGNORE INTO audit_records VALUES ({placeholders})", values)
                        except Exception as e:
                            print(f"Failed to migrate row: {e}")

    def log_decision(self, record: AuditRecord):
        """
        Validates the record and inserts it into the SQLite db.
        """
        record_dict = record.to_csv_dict()
        headers = AuditRecord.get_csv_headers()
        values = [record_dict.get(h, '') for h in headers]
        placeholders = ', '.join(['?'] * len(headers))
        
        with closing(sqlite3.connect(self.filepath)) as conn:
            with conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(f"INSERT INTO audit_records VALUES ({placeholders})", values)
                except sqlite3.IntegrityError:
                    raise ValueError(f"Audit ID {record.audit_id} already exists.")
            
        return record.audit_id

    def log_feedback(self, record: FeedbackRecord):
        """
        Validates the feedback and inserts it into the SQLite db.
        """
        values = [
            record.feedback_id, record.timestamp, record.evaluator_id,
            record.SKU_ID, record.Warehouse_ID, record.Date,
            record.baseline_decision_state, 
            record.scenario_description if record.scenario_description else '',
            record.feedback_type, record.feedback_text
        ]
        placeholders = ', '.join(['?'] * len(values))
        
        with closing(sqlite3.connect(self.filepath)) as conn:
            with conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(f"INSERT INTO feedback_records VALUES ({placeholders})", values)
                except sqlite3.IntegrityError:
                    raise ValueError(f"Feedback ID {record.feedback_id} already exists.")
                
        return record.feedback_id

    @classmethod
    def get_collection_stats(cls, filepath='data/decision_audit_log.db'):
        """Reads from SQLite to return basic monitoring statistics."""
        stats = {
            'total': 0,
            'ACCEPT': 0,
            'REJECT': 0,
            'OVERRIDE': 0,
            'unique_skus_count': 0,
            'unique_whs_count': 0,
            'decision_states': []
        }
        
        if not os.path.exists(filepath):
            return stats
            
        try:
            with closing(sqlite3.connect(filepath)) as conn:
                cursor = conn.cursor()
                
                # Check if table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_records'")
                if not cursor.fetchone():
                    return stats
                    
                cursor.execute("SELECT COUNT(*) FROM audit_records")
                stats['total'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT manager_action, COUNT(*) FROM audit_records GROUP BY manager_action")
                for row in cursor.fetchall():
                    if row[0] in stats:
                        stats[row[0]] = row[1]
                        
                cursor.execute("SELECT COUNT(DISTINCT SKU_ID) FROM audit_records")
                stats['unique_skus_count'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(DISTINCT Warehouse_ID) FROM audit_records")
                stats['unique_whs_count'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT DISTINCT baseline_decision_state FROM audit_records")
                stats['decision_states'] = [r[0] for r in cursor.fetchall() if r[0]]
                
        except sqlite3.Error:
            pass # Return empty stats on error
            
        return stats
