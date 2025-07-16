# KDP Strategist AI Agent

A sophisticated AI-powered agent designed to help Kindle Direct Publishing (KDP) authors and publishers discover profitable niches, analyze market competition, generate optimized book listings, validate trends, and perform comprehensive stress testing on market opportunities.

## 🚀 Features

### Core Capabilities

- **🔍 Niche Discovery**: Intelligent discovery of profitable publishing niches using advanced keyword analysis and market research
- **📊 Competitor Analysis**: Deep analysis of competitor products, pricing strategies, and market positioning
- **📝 Listing Generation**: AI-powered generation of optimized KDP book listings with SEO-friendly titles, descriptions, and keywords
- **📈 Trend Validation**: Comprehensive trend analysis with forecasting and seasonality detection
- **🧪 Stress Testing**: Rigorous testing of niche resilience under various market scenarios

### Technical Features

- **MCP Integration**: Built on the Model Context Protocol for seamless AI assistant integration
- **Multi-API Support**: Integrates with Google Trends and Keepa APIs for comprehensive market data
- **Advanced Caching**: Intelligent caching system supporting file-based, Redis, and in-memory storage
- **Rate Limiting**: Built-in rate limiting and retry logic for API stability
- **Comprehensive Logging**: Detailed logging and monitoring capabilities
- **Data Validation**: Robust data validation and error handling

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Optional: Redis server (for Redis caching)
- API Keys:
  - Keepa API key (for Amazon product data)
  - Google Trends access (via pytrends)

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd PublishingStrategist
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install the Package

```bash
pip install -e .
```

### 5. Configuration

Create a `.env` file in the project root:

```env
# Environment Configuration
ENVIRONMENT=development
DEBUG=true

# API Configuration
KEEPA_API_KEY=your_keepa_api_key_here
KEEPA_RATE_LIMIT=60
TRENDS_RATE_LIMIT=30
API_REQUEST_TIMEOUT=30

# Cache Configuration
CACHE_TYPE=file
CACHE_TTL=3600
CACHE_MAX_SIZE=1000

# Redis Configuration (if using Redis cache)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Business Logic Configuration
MIN_PROFITABILITY_SCORE=50.0
MAX_COMPETITION_SCORE=70.0
TREND_WEIGHT=0.4
COMPETITION_WEIGHT=0.3
PROFITABILITY_WEIGHT=0.3
TRENDS_RATE_LIMIT=50

# Development
DEVELOPMENT_MODE=true
LOG_LEVEL=INFO
```

## 🚀 Usage

### Command Line Interface

#### Start the MCP Server

```bash
kdp_strategist
```

#### Interactive Mode (for testing)

```bash
kdp_strategist --interactive
```

#### Custom Configuration

```bash
kdp_strategist --config custom.env --log-level DEBUG
```

### Python Module

```bash
python -m kdp_strategist.main
```

### Interactive Mode Commands

When running in interactive mode, you can use these commands:

- `help` - Show available commands
- `tools` - List all available tools
- `test <tool_name>` - Test a specific tool with sample data
- `quit` - Exit interactive mode

## 🔧 Available Tools

### 1. Find Profitable Niches

Discover profitable publishing niches based on keyword analysis.

```python
result = await agent.call_tool("find_profitable_niches", {
    "base_keywords": ["cooking", "fitness", "productivity"],
    "max_niches": 5,
    "min_profitability": 70,
    "include_seasonal": True
})
```

### 2. Analyze Competitor ASIN

Analyze specific competitor products on Amazon.

```python
result = await agent.call_tool("analyze_competitor_asin", {
    "asin": "B08EXAMPLE123",
    "include_market_analysis": True,
    "analyze_pricing_history": True
})
```

### 3. Generate KDP Listing

Generate optimized book listings for KDP.

```python
result = await agent.call_tool("generate_kdp_listing", {
    "niche_keyword": "meal prep for beginners",
    "target_audience": "busy professionals",
    "book_type": "cookbook",
    "include_keywords": True
})
```

### 4. Validate Trend

Validate and analyze market trends with forecasting.

```python
result = await agent.call_tool("validate_trend", {
    "keyword": "intermittent fasting",
    "timeframe": "today 12-m",
    "include_forecasts": True,
    "include_seasonality": True
})
```

### 5. Niche Stress Test

Perform comprehensive stress testing on market niches.

```python
result = await agent.call_tool("niche_stress_test", {
    "niche_keyword": "keto diet recipes",
    "include_all_scenarios": True,
    "custom_scenarios": []
})
```

## 📊 Data Models

### Niche Model

Represents a publishing niche with comprehensive metrics:

- **Category**: Primary category/topic
- **Keywords**: Primary and related keywords
- **Scores**: Competition, profitability, market size, confidence
- **Trend Analysis**: Historical and forecasted trend data
- **Competitor Data**: Information about market competitors
- **Content Gaps**: Identified opportunities for content creation
- **Seasonal Factors**: Seasonal patterns and volatility

### KDP Listing Model

Represents an optimized book listing:

- **Title**: SEO-optimized book title
- **Description**: Compelling book description
- **Keywords**: Targeted keywords for discoverability
- **Categories**: Relevant KDP categories
- **Pricing**: Recommended pricing strategy
- **Target Audience**: Defined target readership

### Trend Analysis Model

Represents comprehensive trend analysis:

- **Trend Score**: Numerical trend strength (0-100)
- **Direction**: Rising, stable, or declining
- **Strength**: Weak, moderate, strong, very strong
- **Regional Interest**: Geographic trend distribution
- **Seasonal Patterns**: Cyclical behavior analysis
- **Forecasts**: 1, 3, 6, and 12-month predictions

## 🏗️ Architecture



### Key Components

1. **Agent Layer**: MCP-compatible agent with tool registration and management
2. **Data Layer**: API clients with caching, rate limiting, and error handling
3. **Model Layer**: Structured data models with validation and serialization
4. **Configuration Layer**: Environment-based configuration management

## 🔧 Configuration Options

### Cache Configuration

- **File Cache**: Stores data in local files (default)
- **Redis Cache**: Uses Redis for distributed caching
- **Memory Cache**: In-memory caching for development

### API Configuration

- **Keepa API**: Amazon product data and pricing history
- **Google Trends**: Search trend data and analysis
- **Rate Limiting**: Configurable rate limits for API stability

### Logging Configuration

- **Multiple Loggers**: Separate loggers for different components
- **Multiple Handlers**: Console, file, and structured logging
- **Configurable Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL

## 🧪 Testing

### Interactive Testing

Use the interactive mode to test individual tools:

```bash
kdp_strategist --interactive
```

### Tool Testing

Test specific tools with sample data:

```
KDP Strategist> test find_profitable_niches
KDP Strategist> test validate_trend
```

## 📈 Performance Optimization

### Caching Strategy

- **Multi-level Caching**: Memory, file, and Redis caching
- **TTL Management**: Configurable time-to-live for cached data
- **Cache Invalidation**: Smart cache invalidation strategies

### Rate Limiting

- **API Protection**: Prevents API quota exhaustion
- **Retry Logic**: Exponential backoff for failed requests
- **Circuit Breaker**: Automatic failure detection and recovery

### Batch Processing

- **Keyword Expansion**: Efficient batch processing of keyword variations
- **Trend Analysis**: Batch trend data retrieval and analysis
- **Competitor Analysis**: Parallel processing of competitor data

## 🚨 Error Handling

### Robust Error Management

- **API Failures**: Graceful handling of API errors and timeouts
- **Data Validation**: Comprehensive input and output validation
- **Fallback Strategies**: Alternative data sources when primary APIs fail
- **Logging**: Detailed error logging for debugging and monitoring

### Recovery Mechanisms

- **Retry Logic**: Automatic retry with exponential backoff
- **Circuit Breaker**: Prevents cascade failures
- **Graceful Degradation**: Partial functionality when services are unavailable

## 🔒 Security Considerations

### API Key Management

- **Environment Variables**: Secure storage of API keys
- **No Hardcoding**: API keys never stored in code
- **Validation**: API key validation on startup

### Data Privacy

- **Local Processing**: Sensitive data processed locally
- **Cache Security**: Secure caching of sensitive information
- **Logging Safety**: No sensitive data in logs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### Common Issues

1. **API Key Errors**: Ensure your Keepa API key is valid and has sufficient quota
2. **Rate Limiting**: If you encounter rate limits, increase the delay between requests
3. **Cache Issues**: Clear the cache directory if you encounter stale data
4. **Memory Usage**: Use Redis cache for large-scale operations

### Getting Help

- Check the logs for detailed error information
- Use interactive mode to test individual components
- Review the configuration settings
- Consult the API documentation for external services

## 🔮 Future Enhancements
                                                                                    
- **Machine Learning Models**: Advanced predictive models for niche profitability
- **Real-time Monitoring**: Live market monitoring and alerts
- **Advanced Analytics**: Deeper market analysis and insights
- **Multi-platform Support**: Support for additional publishing platforms
- **Web Interface**: Browser-based interface for easier interaction
- **API Expansion**: Additional data sources and market intelligence

---

**KDP Strategist AI Agent** - Empowering publishers with AI-driven market intelligence.