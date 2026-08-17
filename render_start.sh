#!/bin/bash
set -e

# Render mounts the persistent disk at /var/data
# We cannot mount it at /opt/render/project/src/data because it would hide the CSV datasets

if [ ! -f /var/data/decision_audit_log.db ]; then
    echo "Initializing persistent database from repository..."
    cp data/decision_audit_log.db /var/data/decision_audit_log.db
fi

# Safely symlink the persistent database back to the application's expected path
rm -f data/decision_audit_log.db
ln -s /var/data/decision_audit_log.db data/decision_audit_log.db

# Run verification and start server
python healthcheck.py
python wsgi.py
