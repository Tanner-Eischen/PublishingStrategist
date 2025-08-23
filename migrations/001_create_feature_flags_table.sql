-- Create feature flags tracking table
-- Created: 2025-07-28T21:31:28.966958

-- Create feature flags tracking table
CREATE TABLE IF NOT EXISTS feature_flags_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flag_name VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by VARCHAR(100),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    environment VARCHAR(50) DEFAULT 'production'
);

CREATE INDEX IF NOT EXISTS idx_feature_flags_history_flag_name ON feature_flags_history(flag_name);
CREATE INDEX IF NOT EXISTS idx_feature_flags_history_changed_at ON feature_flags_history(changed_at);