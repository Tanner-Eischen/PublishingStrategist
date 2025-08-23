-- Database initialization script for KDP Strategist
-- This script is run when the PostgreSQL container starts for the first time

-- Create database if it doesn't exist (handled by POSTGRES_DB env var)

-- Create feature flags tracking table
CREATE TABLE IF NOT EXISTS feature_flags_history (
    id SERIAL PRIMARY KEY,
    flag_name VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by VARCHAR(100),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    environment VARCHAR(50) DEFAULT 'production'
);

CREATE INDEX IF NOT EXISTS idx_feature_flags_history_flag_name ON feature_flags_history(flag_name);
CREATE INDEX IF NOT EXISTS idx_feature_flags_history_changed_at ON feature_flags_history(changed_at);

-- Create performance metrics table
CREATE TABLE IF NOT EXISTS performance_metrics (
    id SERIAL PRIMARY KEY,
    client_type VARCHAR(50) NOT NULL,
    keyword VARCHAR(200) NOT NULL,
    response_time REAL NOT NULL,
    success BOOLEAN NOT NULL,
    cache_hit BOOLEAN DEFAULT FALSE,
    confidence_level REAL DEFAULT 0.0,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    environment VARCHAR(50) DEFAULT 'production'
);

CREATE INDEX IF NOT EXISTS idx_performance_metrics_client_type ON performance_metrics(client_type);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_keyword ON performance_metrics(keyword);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_recorded_at ON performance_metrics(recorded_at);

-- Create deployment history table
CREATE TABLE IF NOT EXISTS deployment_history (
    id SERIAL PRIMARY KEY,
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

-- Create rollback events table
CREATE TABLE IF NOT EXISTS rollback_events (
    id SERIAL PRIMARY KEY,
    environment VARCHAR(50) NOT NULL,
    rollback_type VARCHAR(50) NOT NULL,
    reason TEXT NOT NULL,
    triggered_by VARCHAR(100),
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    success BOOLEAN DEFAULT FALSE,
    details JSONB
);

CREATE INDEX IF NOT EXISTS idx_rollback_events_environment ON rollback_events(environment);
CREATE INDEX IF NOT EXISTS idx_rollback_events_triggered_at ON rollback_events(triggered_at);

-- Create system health metrics table
CREATE TABLE IF NOT EXISTS system_health_metrics (
    id SERIAL PRIMARY KEY,
    environment VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value REAL NOT NULL,
    metric_unit VARCHAR(20),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    details JSONB
);

CREATE INDEX IF NOT EXISTS idx_system_health_metrics_environment ON system_health_metrics(environment);
CREATE INDEX IF NOT EXISTS idx_system_health_metrics_name ON system_health_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_system_health_metrics_recorded_at ON system_health_metrics(recorded_at);

-- Insert initial data
INSERT INTO deployment_history (version, environment, deployment_type, status, started_at, completed_at, deployed_by, notes)
VALUES ('initial', 'production', 'initial_setup', 'completed', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'system', 'Initial database setup')
ON CONFLICT DO NOTHING;

-- Create a view for recent deployment status
CREATE OR REPLACE VIEW recent_deployments AS
SELECT 
    environment,
    version,
    deployment_type,
    status,
    started_at,
    completed_at,
    deployed_by,
    notes,
    ROW_NUMBER() OVER (PARTITION BY environment ORDER BY started_at DESC) as rank
FROM deployment_history
WHERE started_at >= CURRENT_TIMESTAMP - INTERVAL '30 days';

-- Create a view for system health summary
CREATE OR REPLACE VIEW system_health_summary AS
SELECT 
    environment,
    metric_name,
    AVG(metric_value) as avg_value,
    MIN(metric_value) as min_value,
    MAX(metric_value) as max_value,
    COUNT(*) as sample_count,
    MAX(recorded_at) as last_recorded
FROM system_health_metrics
WHERE recorded_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
GROUP BY environment, metric_name;

-- Grant permissions (if needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO kdp_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO kdp_user;