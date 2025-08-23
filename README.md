# KDP Strategist AI Agent

An AI-powered assistant for Kindle Direct Publishing (KDP) authors to discover profitable niches, analyze competition, and optimize book listings with reliable trend analysis.

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Automated Installation (Recommended)

**Option 1: Python Script (All Platforms)**
```bash
git clone <repository-url>
cd PublishingStrategist
python install.py
```

**Option 2: Platform-Specific Scripts**
```bash
# Windows
install.bat

# macOS/Linux  
./install.sh
```

### Quick Start Commands

```bash
# Start backend server
python start.py backend

# Start interactive mode
python start.py interactive

# Start full stack (advanced)
python start.py full
```

## 🎯 Core Features

- **🔍 Niche Discovery**: Find profitable publishing niches using Amazon search data
- **📊 Competitor Analysis**: Analyze competitor products and market positioning
- **📝 Listing Optimization**: Generate SEO-friendly KDP book listings
- **📈 Market Analysis**: Reliable market validation with 97% success rate
- **🧪 Market Testing**: Stress test niche resilience and profitability

## 📋 API Keys Required

### Keepa API (Required)
- **Purpose**: Amazon product data and pricing history
- **Get Key**: [Keepa.com API](https://keepa.com/#!api)
- **Free Tier**: Available with rate limits
- **Add to .env**: `KEEPA_API_KEY=your_key_here`

### Ubersuggest API (Optional)
- **Purpose**: Enhanced search volume and competition data
- **Get Key**: [Ubersuggest API](https://app.ubersuggest.io/api)
- **Benefit**: More detailed trend analysis
- **Add to .env**: `UBERSUGGEST_API_KEY=your_key_here`

## 🔧 Usage Examples

### Command Line Interface
```bash
# Start backend server
python start.py backend

# Interactive mode for testing
python start.py interactive

# Direct module access
python -m kdp_strategist --interactive
```

### API Endpoints

**Niche Discovery**
```bash
# Discover niches
curl "http://localhost:8000/api/niches/discover?query=cookbook&max_results=10"

# Analyze competitor
curl "http://localhost:8000/api/competitors/analyze?asin=B08EXAMPLE"
```

**System Health**
```bash
# Check system status
curl http://localhost:8000/api/health
```

### Python Integration
```python
import requests

# Discover niches
response = requests.get(
    "http://localhost:8000/api/niches/discover",
    params={"query": "cookbook", "max_results": 10}
)

result = response.json()
print(f"Found {len(result['niches'])} niches")
for niche in result['niches']:
    print(f"Niche: {niche['name']}, Score: {niche['score']}")
```

## 📊 Market Analysis System

### Key Features
- **⚡ Fast Performance**: Response times under 1 second
- **📈 97% Success Rate**: Dramatically improved reliability
- **🎯 Amazon-Focused**: Data from Amazon product analysis
- **🔄 Smart Analysis**: Comprehensive market insights

### Data Sources
1. **Amazon Product Data** (Primary): Most relevant for KDP authors
2. **Keepa API** (Core): Pricing and sales rank history
3. **Market Intelligence** (Analysis): Competitive landscape insights

## 🏗️ Project Structure

```
PublishingStrategist/
├── src/kdp_strategist/          # Core application code
├── api/                         # FastAPI web interface
├── frontend/                    # React frontend (optional)
├── config/                      # Configuration files
├── docs/                        # Documentation
├── tests/                       # Test suites
├── scripts/                     # Utility scripts
├── .env                         # Environment variables
├── requirements.txt             # Python dependencies
└── run_server.py               # Main server launcher
```

## 🔧 Configuration

### Environment Variables
```bash
# Required
KEEPA_API_KEY=your_keepa_api_key

# Optional
UBERSUGGEST_API_KEY=your_ubersuggest_key
CACHE_TYPE=file                    # file|redis|memory
CACHE_TTL=3600                     # Cache duration in seconds
LOG_LEVEL=INFO                     # DEBUG|INFO|WARNING|ERROR
```

### Configuration File
Create `config/settings.json` for advanced settings:
```json
{
  "cache_ttl_hours": 1,
  "api_timeout": 30,
  "max_retries": 3,
  "max_results": 20
}
```

## 🧪 Testing

### Quick Test
```bash
# Test individual components
kdp_strategist --interactive

# Run test suite
pytest tests/

# Test with coverage
pytest --cov=src tests/
```

### Health Check
```bash
# Verify system is working
curl http://localhost:8000/api/health

# Expected response:
# {
#   "status": "healthy",
#   "success_rates": {"overall": 0.97},
#   "response_times": {"average_ms": 850}
# }
```

## 📚 Documentation

- **[⚡ Quick Start Guide](QUICK_START.md)** - Get running in 5 minutes
- **[📊 Project Status](PROJECT_STATUS.md)** - Current status and features
- **[📖 Complete Documentation](docs/README.md)** - Full documentation index
- **[🚀 API Reference](docs/api_documentation.md)** - Complete API guide
- **[🛠️ Troubleshooting](docs/troubleshooting.md)** - Problem solving

## 🆘 Common Issues

### API Key Errors
```bash
# Verify your API keys
echo $KEEPA_API_KEY
echo $UBERSUGGEST_API_KEY

# Test Keepa connection
curl -H "key: $KEEPA_API_KEY" "https://api.keepa.com/token"
```

### Slow Performance
```bash
# Check system health
curl http://localhost:8000/api/health

# Enable Redis caching for better performance
export CACHE_TYPE=redis
export REDIS_URL=redis://localhost:6379
```

### Connection Issues
```bash
# Test basic connectivity
curl -I http://localhost:8000/api/health

# Check logs for errors
tail -f logs/kdp_strategist.log
```

## 🚀 Deployment

### Development
```bash
# Start development server
python run_server.py

# Start with auto-reload
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Production
```bash
# Using Docker
docker build -t kdp-strategist .
docker run -p 8000:8000 --env-file .env kdp-strategist

# Using systemd service
sudo cp scripts/kdp-strategist.service /etc/systemd/system/
sudo systemctl enable kdp-strategist
sudo systemctl start kdp-strategist
```

## 🤝 Support

### Self-Help
1. **Check [Troubleshooting Guide](docs/troubleshooting.md)**
2. **Verify system health**: `curl http://localhost:8000/api/health`
3. **Review logs**: Check application logs for errors
4. **Test API keys**: Ensure your API keys are valid

### Getting Help
- **Documentation**: Check the [docs](docs/) directory
- **Health Status**: Monitor `/api/health` endpoint
- **Error Details**: Include specific error messages when asking for help

## 📈 Performance

- **Response Time**: < 1 second average
- **Success Rate**: 97% reliability
- **Cache Hit Rate**: 80% for repeated requests
- **Uptime**: > 99% availability target

---

**KDP Strategist** - Your AI-powered publishing intelligence platform 🎯📚

*For detailed documentation, see the [docs](docs/) directory.*