#!/usr/bin/env python3
"""
Monitoring Dashboard Setup Script

This script sets up and configures the production monitoring dashboard
with Prometheus, Grafana, and other monitoring tools.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

def create_prometheus_config():
    """Create Prometheus configuration file."""
    config = {
        'global': {
            'scrape_interval': '15s',
            'evaluation_interval': '15s'
        },
        'rule_files': [
            'monitoring/alert_rules.yml'
        ],
        'alerting': {
            'alertmanagers': [
                {
                    'static_configs': [
                        {'targets': ['alertmanager:9093']}
                    ]
                }
            ]
        },
        'scrape_configs': [
            {
                'job_name': 'kdp-strategist',
                'static_configs': [
                    {'targets': ['localhost:8000']}
                ],
                'metrics_path': '/api/monitoring/metrics/prometheus',
                'scrape_interval': '30s'
            },
            {
                'job_name': 'node-exporter',
                'static_configs': [
                    {'targets': ['localhost:9100']}
                ]
            }
        ]
    }
    
    # Write YAML format (simplified)
    with open('monitoring/prometheus.yml', 'w') as f:
        f.write(f"""# Prometheus configuration for KDP Strategist
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  - job_name: 'kdp-strategist'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/monitoring/metrics/prometheus'
    scrape_interval: 30s
    
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
""")
    
    print("✓ Created Prometheus configuration")

def create_grafana_dashboard():
    """Create Grafana dashboard configuration."""
    dashboard = {
        "dashboard": {
            "id": None,
            "title": "KDP Strategist Production Monitoring",
            "tags": ["kdp-strategist", "production"],
            "timezone": "browser",
            "panels": [
                {
                    "id": 1,
                    "title": "System Health Score",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "system_health_score",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "color": {
                                "mode": "thresholds"
                            },
                            "thresholds": {
                                "steps": [
                                    {"color": "red", "value": 0},
                                    {"color": "yellow", "value": 50},
                                    {"color": "green", "value": 80}
                                ]
                            },
                            "unit": "percent"
                        }
                    },
                    "gridPos": {"h": 8, "w": 6, "x": 0, "y": 0}
                },
                {
                    "id": 2,
                    "title": "Response Time",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "avg_response_time_ms",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "ms"
                        }
                    },
                    "gridPos": {"h": 8, "w": 12, "x": 6, "y": 0}
                },
                {
                    "id": 3,
                    "title": "Error Rate",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "error_rate_percent",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percent"
                        }
                    },
                    "gridPos": {"h": 8, "w": 6, "x": 18, "y": 0}
                },
                {
                    "id": 4,
                    "title": "Cache Hit Rate",
                    "type": "gauge",
                    "targets": [
                        {
                            "expr": "cache_hit_rate_percent",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "percent",
                            "min": 0,
                            "max": 100
                        }
                    },
                    "gridPos": {"h": 8, "w": 6, "x": 0, "y": 8}
                },
                {
                    "id": 5,
                    "title": "Throughput",
                    "type": "timeseries",
                    "targets": [
                        {
                            "expr": "requests_per_minute",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "reqps"
                        }
                    },
                    "gridPos": {"h": 8, "w": 12, "x": 6, "y": 8}
                },
                {
                    "id": 6,
                    "title": "Active Alerts",
                    "type": "stat",
                    "targets": [
                        {
                            "expr": "active_alerts_count",
                            "refId": "A"
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "color": {
                                "mode": "thresholds"
                            },
                            "thresholds": {
                                "steps": [
                                    {"color": "green", "value": 0},
                                    {"color": "yellow", "value": 1},
                                    {"color": "red", "value": 5}
                                ]
                            }
                        }
                    },
                    "gridPos": {"h": 8, "w": 6, "x": 18, "y": 8}
                }
            ],
            "time": {
                "from": "now-1h",
                "to": "now"
            },
            "refresh": "30s"
        }
    }
    
    os.makedirs('monitoring/grafana', exist_ok=True)
    with open('monitoring/grafana/kdp-strategist-dashboard.json', 'w') as f:
        json.dump(dashboard, f, indent=2)
    
    print("✓ Created Grafana dashboard configuration")

def create_docker_compose():
    """Create Docker Compose file for monitoring stack."""
    compose_content = """version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: kdp-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring:/etc/prometheus
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: kdp-grafana
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana:/etc/grafana/provisioning/dashboards
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    restart: unless-stopped

  alertmanager:
    image: prom/alertmanager:latest
    container_name: kdp-alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml
      - alertmanager_data:/alertmanager
    restart: unless-stopped

  node-exporter:
    image: prom/node-exporter:latest
    container_name: kdp-node-exporter
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    restart: unless-stopped

volumes:
  prometheus_data:
  grafana_data:
  alertmanager_data:
"""
    
    with open('docker-compose.monitoring.yml', 'w') as f:
        f.write(compose_content)
    
    print("✓ Created Docker Compose configuration for monitoring stack")

def create_alertmanager_config():
    """Create Alertmanager configuration."""
    config = """global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'monitoring@kdpstrategist.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
- name: 'web.hook'
  email_configs:
  - to: 'admin@kdpstrategist.com'
    subject: 'KDP Strategist Alert: {{ .GroupLabels.alertname }}'
    body: |
      {{ range .Alerts }}
      Alert: {{ .Annotations.summary }}
      Description: {{ .Annotations.description }}
      {{ end }}

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'dev', 'instance']
"""
    
    with open('monitoring/alertmanager.yml', 'w') as f:
        f.write(config)
    
    print("✓ Created Alertmanager configuration")

def create_monitoring_scripts():
    """Create monitoring utility scripts."""
    
    # Health check script
    health_check_script = """#!/bin/bash
# Health check script for KDP Strategist monitoring

echo "Checking KDP Strategist monitoring health..."

# Check if monitoring API is responding
if curl -s http://localhost:8000/api/monitoring/health > /dev/null; then
    echo "✓ Monitoring API is responding"
else
    echo "✗ Monitoring API is not responding"
    exit 1
fi

# Check Prometheus
if curl -s http://localhost:9090/-/healthy > /dev/null; then
    echo "✓ Prometheus is healthy"
else
    echo "✗ Prometheus is not healthy"
fi

# Check Grafana
if curl -s http://localhost:3000/api/health > /dev/null; then
    echo "✓ Grafana is healthy"
else
    echo "✗ Grafana is not healthy"
fi

echo "Health check completed"
"""
    
    with open('scripts/monitoring_health_check.sh', 'w') as f:
        f.write(health_check_script)
    os.chmod('scripts/monitoring_health_check.sh', 0o755)
    
    # Backup script
    backup_script = """#!/bin/bash
# Backup monitoring data

BACKUP_DIR="backups/monitoring/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Creating monitoring backup in $BACKUP_DIR..."

# Backup Prometheus data
if [ -d "/var/lib/docker/volumes/publishingstrategist_prometheus_data" ]; then
    cp -r /var/lib/docker/volumes/publishingstrategist_prometheus_data "$BACKUP_DIR/prometheus"
    echo "✓ Prometheus data backed up"
fi

# Backup Grafana data
if [ -d "/var/lib/docker/volumes/publishingstrategist_grafana_data" ]; then
    cp -r /var/lib/docker/volumes/publishingstrategist_grafana_data "$BACKUP_DIR/grafana"
    echo "✓ Grafana data backed up"
fi

# Backup configuration files
cp -r monitoring "$BACKUP_DIR/config"
echo "✓ Configuration files backed up"

# Export current dashboard data
curl -s http://localhost:8000/api/monitoring/dashboard/export > "$BACKUP_DIR/dashboard_export.json"
echo "✓ Dashboard data exported"

echo "Backup completed: $BACKUP_DIR"
"""
    
    with open('scripts/backup_monitoring.sh', 'w') as f:
        f.write(backup_script)
    os.chmod('scripts/backup_monitoring.sh', 0o755)
    
    print("✓ Created monitoring utility scripts")

def setup_systemd_service():
    """Create systemd service file for monitoring."""
    service_content = f"""[Unit]
Description=KDP Strategist Production Monitoring
After=network.target

[Service]
Type=simple
User=kdp
WorkingDirectory={os.getcwd()}
ExecStart=/usr/bin/python3 {os.getcwd()}/scripts/start_production_monitoring.py --daemon
Restart=always
RestartSec=10
Environment=PYTHONPATH={os.getcwd()}/src

[Install]
WantedBy=multi-user.target
"""
    
    service_file = '/etc/systemd/system/kdp-monitoring.service'
    
    print(f"To install systemd service, run as root:")
    print(f"sudo tee {service_file} << 'EOF'")
    print(service_content)
    print("EOF")
    print("sudo systemctl daemon-reload")
    print("sudo systemctl enable kdp-monitoring")
    print("sudo systemctl start kdp-monitoring")

def main():
    """Main setup function."""
    print("Setting up KDP Strategist Production Monitoring...")
    
    # Create directories
    os.makedirs('monitoring', exist_ok=True)
    os.makedirs('monitoring/grafana', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    os.makedirs('backups/monitoring', exist_ok=True)
    
    # Create configuration files
    create_prometheus_config()
    create_grafana_dashboard()
    create_alertmanager_config()
    create_docker_compose()
    create_monitoring_scripts()
    
    print("\n" + "="*60)
    print("Production Monitoring Setup Complete!")
    print("="*60)
    
    print("\nNext steps:")
    print("1. Start the monitoring stack:")
    print("   docker-compose -f docker-compose.monitoring.yml up -d")
    print("\n2. Start KDP Strategist monitoring:")
    print("   python scripts/start_production_monitoring.py")
    print("\n3. Access dashboards:")
    print("   - Prometheus: http://localhost:9090")
    print("   - Grafana: http://localhost:3000 (admin/admin)")
    print("   - KDP Strategist: http://localhost:8000/monitoring")
    print("\n4. Optional: Install systemd service:")
    setup_systemd_service()
    
    print("\n5. Run health check:")
    print("   ./scripts/monitoring_health_check.sh")
    
    print("\nConfiguration files created:")
    print("- monitoring/prometheus.yml")
    print("- monitoring/alertmanager.yml")
    print("- monitoring/grafana/kdp-strategist-dashboard.json")
    print("- docker-compose.monitoring.yml")
    print("- scripts/monitoring_health_check.sh")
    print("- scripts/backup_monitoring.sh")

if __name__ == "__main__":
    main()