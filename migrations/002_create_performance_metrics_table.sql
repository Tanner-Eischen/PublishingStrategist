-- Create performance metrics tracking table
-- Created: 2025-07-28T21:31:29.197373

-- Create performance metrics table
CREATE TABLE IF NOT EXISTS performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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