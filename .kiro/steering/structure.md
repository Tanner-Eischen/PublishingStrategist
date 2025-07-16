# Project Structure

## Root Directory Layout

```
PublishingStrategist/
├── .env                    # Environment variables
├── .gitignore             # Git ignore rules
├── README.md              # Project documentation
├── requirements.txt       # Python dependencies
├── setup.py              # Package installation config
├── TASKS.md              # Development tasks/todos
├── kdp-strategist.mcp.json # MCP server configuration
├── start_kdp_strategist.py # Full-stack launcher
├── run_server.py         # Backend server launcher
├── start_frontend.py     # Frontend launcher
└── example_usage.md      # Usage examples
```

## Core Application Structure

### Backend (`/api`)
```
api/
├── main.py              # FastAPI application entry point
├── __init__.py         # Package initialization
├── models/             # Data models and schemas
├── routers/            # API route handlers
└── __pycache__/        # Python bytecode cache
```

### Source Code (`/src`)
```
src/
└── kdp_strategist/     # Main package source
    ├── __init__.py     # Package initialization
    ├── agent/          # MCP agent implementation
    ├── data/           # Data processing modules
    ├── models/         # Business logic models
    └── utils/          # Utility functions
```

### Configuration (`/config`)
```
config/
├── settings.py         # Application settings
├── logging.conf        # Logging configuration
└── __pycache__/        # Python bytecode cache
```

### Frontend (`/frontend`)
```
frontend/
├── package.json        # Node.js dependencies
├── package-lock.json   # Dependency lock file
├── tailwind.config.js  # Tailwind CSS configuration
├── .env               # Frontend environment variables
├── public/            # Static assets
└── src/               # React source code
    ├── components/    # Reusable UI components
    ├── pages/         # Page components
    ├── hooks/         # Custom React hooks
    ├── utils/         # Utility functions
    └── styles/        # CSS and styling
```

## Supporting Directories

### Examples & Documentation
```
examples/
└── basic_usage.py      # Example usage scripts

PRPs/
└── templates/          # Project requirement templates
```

### Development & Build
```
cache/                  # File-based caching directory
venv/                   # Python virtual environment
.git/                   # Git repository data
.kiro/                  # Kiro IDE configuration
    └── steering/       # AI assistant steering rules
```

## Key File Conventions

### Python Files
- **Entry Points**: `start_*.py` files for launching different components
- **Main Modules**: `main.py` for primary application logic
- **Configuration**: `settings.py` for centralized configuration
- **Models**: Pydantic models for data validation and serialization

### Frontend Files
- **Components**: React components in `/src/components`
- **Pages**: Route-level components in `/src/pages`
- **Configuration**: `tailwind.config.js` for styling, `package.json` for dependencies

### Configuration Files
- **Environment**: `.env` files for environment-specific settings
- **Package Management**: `requirements.txt` (Python), `package.json` (Node.js)
- **Build/Deploy**: `setup.py` for Python package installation

## Import Patterns

### Python Imports
```python
# Relative imports within package
from .models import NicheModel
from ..utils import cache_manager

# Absolute imports for external dependencies
from fastapi import FastAPI
from pydantic import BaseModel
```

### Module Organization
- **Business Logic**: Core functionality in `/src/kdp_strategist`
- **API Layer**: Web interface in `/api`
- **Configuration**: Settings and config in `/config`
- **Examples**: Usage examples in `/examples`

## Development Workflow

1. **Backend Development**: Work in `/src` and `/api` directories
2. **Frontend Development**: Work in `/frontend` directory
3. **Configuration**: Modify settings in `/config` and `.env` files
4. **Testing**: Use `/examples` for integration testing
5. **Documentation**: Update README.md and example files