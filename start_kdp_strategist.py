#!/usr/bin/env python3
"""
KDP Strategist Full Stack Launcher

This script provides options to start the KDP Strategist application:
1. Backend only (FastAPI server)
2. Frontend only (React development server)
3. Full stack (both backend and frontend)
4. Production mode
"""

import os
import sys
import time
import signal
import argparse
import subprocess
import threading
from pathlib import Path
from typing import List, Optional


class KDPStrategistLauncher:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.frontend_dir = self.project_root / 'frontend'
        self.processes: List[subprocess.Popen] = []
        self.shutdown_event = threading.Event()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print("\n🛑 Shutting down KDP Strategist...")
        self.shutdown_event.set()
        self._cleanup_processes()
        sys.exit(0)
    
    def _cleanup_processes(self):
        """Clean up all running processes."""
        for process in self.processes:
            if process.poll() is None:  # Process is still running
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                except Exception as e:
                    print(f"Error terminating process: {e}")
        self.processes.clear()
    
    def check_dependencies(self) -> bool:
        """Check if all required dependencies are available."""
        print("🔍 Checking dependencies...")
        
        # Check Python dependencies
        try:
            import fastapi
            import uvicorn
            print("✅ FastAPI dependencies found")
        except ImportError:
            print("❌ FastAPI dependencies missing. Run: pip install -r requirements.txt")
            return False
        
        # Check Node.js for frontend
        try:
            result = subprocess.run(['node', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Node.js found: {result.stdout.strip()}")
            else:
                print("❌ Node.js not found")
                return False
        except FileNotFoundError:
            print("❌ Node.js not found. Install from https://nodejs.org/")
            return False
        
        return True
    
    def start_backend(self, port: int = 8000, reload: bool = True) -> Optional[subprocess.Popen]:
        """Start the FastAPI backend server."""
        print(f"🚀 Starting backend server on port {port}...")
        
        try:
            env = os.environ.copy()
            env['PORT'] = str(port)
            env['RELOAD'] = 'true' if reload else 'false'
            
            process = subprocess.Popen(
                [sys.executable, 'run_server.py'],
                cwd=self.project_root,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            self.processes.append(process)
            
            # Wait a moment to check if the process started successfully
            time.sleep(2)
            if process.poll() is not None:
                print("❌ Backend server failed to start")
                return None
            
            print(f"✅ Backend server started (PID: {process.pid})")
            return process
            
        except Exception as e:
            print(f"❌ Failed to start backend: {e}")
            return None
    
    def start_frontend(self, api_url: str = "http://localhost:8000") -> Optional[subprocess.Popen]:
        """Start the React frontend development server."""
        print("🌐 Starting frontend development server...")
        
        if not self.frontend_dir.exists():
            print(f"❌ Frontend directory not found: {self.frontend_dir}")
            return None
        
        try:
            # Create .env file
            self._create_frontend_env(api_url)
            
            # Check if dependencies are installed
            if not self._check_frontend_dependencies():
                if not self._install_frontend_dependencies():
                    return None
            
            # Determine package manager
            package_manager = self._get_package_manager()
            if not package_manager:
                return None
            
            # Start the development server
            env = os.environ.copy()
            env['REACT_APP_API_URL'] = api_url
            env['BROWSER'] = 'none'
            
            cmd = ['yarn', 'start'] if package_manager == 'yarn' else ['npm', 'start']
            
            process = subprocess.Popen(
                cmd,
                cwd=self.frontend_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            self.processes.append(process)
            
            # Wait for the server to start
            time.sleep(5)
            if process.poll() is not None:
                print("❌ Frontend server failed to start")
                return None
            
            print(f"✅ Frontend server started (PID: {process.pid})")
            return process
            
        except Exception as e:
            print(f"❌ Failed to start frontend: {e}")
            return None
    
    def _create_frontend_env(self, api_url: str):
        """Create .env file for React app."""
        env_file = self.frontend_dir / '.env'
        
        env_content = f"""# KDP Strategist Frontend Environment Variables
REACT_APP_API_URL={api_url}
REACT_APP_NAME=KDP Strategist
REACT_APP_VERSION=1.0.0
GENERATE_SOURCEMAP=true
REACT_APP_ENV=development
BROWSER=none
"""
        
        with open(env_file, 'w') as f:
            f.write(env_content)
    
    def _check_frontend_dependencies(self) -> bool:
        """Check if frontend dependencies are installed."""
        node_modules = self.frontend_dir / 'node_modules'
        return node_modules.exists() and any(node_modules.iterdir())
    
    def _install_frontend_dependencies(self) -> bool:
        """Install frontend dependencies."""
        print("📦 Installing frontend dependencies...")
        
        package_manager = self._get_package_manager()
        if not package_manager:
            return False
        
        try:
            cmd = ['yarn', 'install'] if package_manager == 'yarn' else ['npm', 'install']
            result = subprocess.run(
                cmd,
                cwd=self.frontend_dir,
                check=True,
                capture_output=True,
                text=True
            )
            print("✅ Frontend dependencies installed")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install frontend dependencies: {e}")
            return False
    
    def _get_package_manager(self) -> Optional[str]:
        """Get available package manager."""
        try:
            subprocess.run(['yarn', '--version'], capture_output=True, check=True)
            return 'yarn'
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        
        try:
            subprocess.run(['npm', '--version'], capture_output=True, check=True)
            return 'npm'
        except (FileNotFoundError, subprocess.CalledProcessError):
            print("❌ No package manager found (npm or yarn required)")
            return None
    
    def print_status(self, backend_port: int = 8000, frontend_port: int = 3000):
        """Print application status and URLs."""
        print("\n" + "="*70)
        print("🎯 KDP Strategist Application Status")
        print("="*70)
        print(f"🔗 Frontend URL: http://localhost:{frontend_port}")
        print(f"🔗 Backend API: http://localhost:{backend_port}")
        print(f"📖 API Documentation: http://localhost:{backend_port}/docs")
        print(f"🔧 Interactive API: http://localhost:{backend_port}/redoc")
        print("="*70)
        print("Press Ctrl+C to stop all servers")
        print("="*70 + "\n")
    
    def monitor_processes(self):
        """Monitor running processes and restart if needed."""
        while not self.shutdown_event.is_set():
            for i, process in enumerate(self.processes[:]):
                if process.poll() is not None:
                    print(f"⚠️ Process {process.pid} has stopped")
                    self.processes.remove(process)
            
            time.sleep(5)
    
    def run_fullstack(self, backend_port: int = 8000, frontend_port: int = 3000):
        """Run both backend and frontend servers."""
        print("🚀 Starting KDP Strategist Full Stack...")
        
        if not self.check_dependencies():
            return False
        
        # Start backend
        backend_process = self.start_backend(port=backend_port)
        if not backend_process:
            return False
        
        # Wait for backend to be ready
        time.sleep(3)
        
        # Start frontend
        frontend_process = self.start_frontend(f"http://localhost:{backend_port}")
        if not frontend_process:
            self._cleanup_processes()
            return False
        
        # Print status
        self.print_status(backend_port, frontend_port)
        
        # Monitor processes
        try:
            self.monitor_processes()
        except KeyboardInterrupt:
            pass
        
        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='KDP Strategist Application Launcher')
    parser.add_argument(
        'mode',
        choices=['backend', 'frontend', 'fullstack', 'full'],
        help='Launch mode: backend only, frontend only, or full stack'
    )
    parser.add_argument(
        '--backend-port',
        type=int,
        default=8000,
        help='Backend server port (default: 8000)'
    )
    parser.add_argument(
        '--frontend-port',
        type=int,
        default=3000,
        help='Frontend server port (default: 3000)'
    )
    parser.add_argument(
        '--no-reload',
        action='store_true',
        help='Disable auto-reload for backend server'
    )
    
    args = parser.parse_args()
    
    launcher = KDPStrategistLauncher()
    
    try:
        if args.mode == 'backend':
            if not launcher.check_dependencies():
                sys.exit(1)
            
            process = launcher.start_backend(
                port=args.backend_port,
                reload=not args.no_reload
            )
            
            if process:
                print(f"🔗 Backend API: http://localhost:{args.backend_port}")
                print(f"📖 API Docs: http://localhost:{args.backend_port}/docs")
                print("Press Ctrl+C to stop")
                process.wait()
            else:
                sys.exit(1)
        
        elif args.mode == 'frontend':
            process = launcher.start_frontend(f"http://localhost:{args.backend_port}")
            
            if process:
                print(f"🔗 Frontend: http://localhost:{args.frontend_port}")
                print("Press Ctrl+C to stop")
                process.wait()
            else:
                sys.exit(1)
        
        elif args.mode in ['fullstack', 'full']:
            success = launcher.run_fullstack(
                backend_port=args.backend_port,
                frontend_port=args.frontend_port
            )
            
            if not success:
                sys.exit(1)
    
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        launcher._cleanup_processes()


if __name__ == "__main__":
    main()