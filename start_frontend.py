#!/usr/bin/env python3
"""
KDP Strategist Frontend Development Server Launcher

This script starts the React development server for the KDP Strategist web UI.
It handles npm/yarn detection, dependency installation, and server startup.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def check_node_installed():
    """Check if Node.js is installed."""
    try:
        result = subprocess.run(['node', '-v'], capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ Node.js found: {version}")
            return True
    except FileNotFoundError:
        pass
    
    print("❌ Node.js not found. Please install Node.js from https://nodejs.org/")
    return False


def check_package_manager():
    """Check which package manager is available (npm or yarn)."""
    # Check for yarn first (often faster)
    if shutil.which('yarn'):
        try:
            result = subprocess.run(['yarn', '-v'], capture_output=True, text=True, shell=True)
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"✅ Yarn found: {version}")
                return 'yarn'
        except FileNotFoundError:
            pass
    
    # Check for npm - try multiple approaches for Windows compatibility
    npm_commands = ['npm', 'npm.cmd', 'npm.exe']
    
    for npm_cmd in npm_commands:
        if shutil.which(npm_cmd):
            try:
                result = subprocess.run([npm_cmd, '-v'], capture_output=True, text=True, shell=True)
                if result.returncode == 0:
                    version = result.stdout.strip()
                    print(f"✅ npm found: {version}")
                    return 'npm'
            except FileNotFoundError:
                continue
    
    # Fallback: try running npm directly without shutil.which check
    try:
        result = subprocess.run(['npm', '-v'], capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ npm found: {version}")
            return 'npm'
    except FileNotFoundError:
        pass
    
    print("❌ No package manager found. Please install npm or yarn.")
    return None


def install_dependencies(package_manager, frontend_dir):
    """Install frontend dependencies."""
    print(f"📦 Installing dependencies with {package_manager}...")
    
    try:
        if package_manager == 'yarn':
            cmd = ['yarn', 'install']
        else:
            cmd = ['npm', 'install']
        
        result = subprocess.run(
            cmd,
            cwd=frontend_dir,
            check=True,
            capture_output=False,
            shell=True
        )
        
        print("✅ Dependencies installed successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False


def check_dependencies_installed(frontend_dir):
    """Check if node_modules exists and has content."""
    node_modules = frontend_dir / 'node_modules'
    return node_modules.exists() and any(node_modules.iterdir())


def start_dev_server(package_manager, frontend_dir):
    """Start the React development server."""
    print(f"🚀 Starting React development server with {package_manager}...")
    
    try:
        if package_manager == 'yarn':
            cmd = ['yarn', 'start']
        else:
            cmd = ['npm', 'start']
        
        # Set environment variables
        env = os.environ.copy()
        env['REACT_APP_API_URL'] = 'http://localhost:8000'
        env['BROWSER'] = 'none'  # Don't auto-open browser
        
        print("\n" + "="*60)
        print("🌐 KDP Strategist Frontend Development Server")
        print("="*60)
        print("📍 Frontend URL: http://localhost:3000")
        print("🔗 API Backend: http://localhost:8000")
        print("📖 Make sure the backend server is running!")
        print("="*60)
        print("Press Ctrl+C to stop the server")
        print("="*60 + "\n")
        
        # Start the server
        subprocess.run(
            cmd,
            cwd=frontend_dir,
            env=env,
            check=True,
            shell=True
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Development server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start development server: {e}")
        return False
    
    return True


def create_env_file(frontend_dir):
    """Create .env file for React app if it doesn't exist."""
    env_file = frontend_dir / '.env'
    
    if not env_file.exists():
        print("📝 Creating .env file...")
        
        env_content = """# KDP Strategist Frontend Environment Variables

# API Backend URL
REACT_APP_API_URL=http://localhost:8000

# App Configuration
REACT_APP_NAME=KDP Strategist
REACT_APP_VERSION=1.0.0

# Development Settings
GENERATE_SOURCEMAP=true
REACT_APP_ENV=development

# Disable automatic browser opening
BROWSER=none

# Port configuration (optional)
# PORT=3000
"""
        
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        print("✅ .env file created successfully!")


def main():
    """Main entry point."""
    print("🎯 KDP Strategist Frontend Launcher")
    print("="*40)
    
    # Get frontend directory
    frontend_dir = Path(__file__).parent / 'frontend'
    
    if not frontend_dir.exists():
        print(f"❌ Frontend directory not found: {frontend_dir}")
        sys.exit(1)
    
    # Check Node.js
    if not check_node_installed():
        sys.exit(1)
    
    # Check package manager
    package_manager = check_package_manager()
    if not package_manager:
        sys.exit(1)
    
    # Create .env file
    create_env_file(frontend_dir)
    
    # Check if dependencies are installed
    if not check_dependencies_installed(frontend_dir):
        print("📦 Dependencies not found. Installing...")
        if not install_dependencies(package_manager, frontend_dir):
            sys.exit(1)
    else:
        print("✅ Dependencies already installed")
    
    # Start development server
    if not start_dev_server(package_manager, frontend_dir):
        sys.exit(1)


if __name__ == "__main__":
    main()