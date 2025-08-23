-- Create deployment history tracking table
-- Created: 2025-07-28T21:31:29.254133

-- Create deployment history table
CREATE TABLE IF NOT EXISTS deployment_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version VARCHAR(100) NOT NULL,
    environment VARCHAR(50) NOT NULL,
    deployment_type VARCHAR(50) DEFAULT 'blue_green',
    status VARCHAR(50) NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    deployed_by VARCHAR(100),
    rollback_version VARCHAR(100),
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_deployment_history_environment ON deployment_history(environment);
CREATE INDEX IF NOT EXISTS idx_deployment_history_version ON deployment_history(version);
CREATE INDEX IF NOT EXISTS idx_deployment_history_started_at ON deployment_history(started_at);