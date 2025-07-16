# Technology Stack

## Backend Stack

- **Python 3.8+**: Core runtime environment
- **FastAPI**: Web framework for REST API and web interface
- **Uvicorn**: ASGI server for FastAPI applications
- **MCP (Model Context Protocol)**: AI assistant integration framework
- **Pydantic**: Data validation and settings management

## Frontend Stack

- **React 18**: Frontend framework
- **TypeScript**: Type-safe JavaScript development
- **Tailwind CSS**: Utility-first CSS framework
- **Chart.js & Recharts**: Data visualization libraries
- **React Router**: Client-side routing

## Data & APIs

- **Keepa API**: Amazon product data and pricing history
- **Google Trends (pytrends)**: Search trend analysis
- **Pandas & NumPy**: Data processing and analysis
- **Scikit-learn**: Machine learning utilities
- **Sentence Transformers**: Text embeddings for similarity analysis

## Caching & Storage

- **Redis**: Distributed caching (optional)
- **File-based caching**: Default caching mechanism
- **In-memory caching**: Development and testing

## Development Tools

- **pytest**: Testing framework
- **Black**: Code formatting
- **Flake8**: Linting
- **MyPy**: Type checking

## Common Commands

### Backend Development
```bash
# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .

# Start backend server
python run_server.py
# or
kdp_strategist

# Start in interactive mode
kdp_strategist --interactive
```

### Frontend Development
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
# or
yarn install

# Start development server
npm start
# or
yarn start

# Build for production
npm run build
```

### Full Stack Development
```bash
# Start both backend and frontend
python start_kdp_strategist.py fullstack

# Start only backend
python start_kdp_strategist.py backend

# Start only frontend
python start_kdp_strategist.py frontend
```

### Testing
```bash
# Run Python tests
pytest

# Run with coverage
pytest --cov=src

# Interactive testing mode
kdp_strategist --interactive
```

## Environment Configuration

Required environment variables in `.env`:
- `KEEPA_API_KEY`: Keepa API access key
- `CACHE_TYPE`: file|redis|memory
- `REDIS_URL`: Redis connection string (if using Redis)
- `LOG_LEVEL`: DEBUG|INFO|WARNING|ERROR