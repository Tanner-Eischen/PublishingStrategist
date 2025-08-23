#!/usr/bin/env python3
"""
KDP Strategist - Simple Startup Script
Unified script to start the KDP Strategist system
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path


def check_environment():
    """Check if the environment is properly set up."""
    if not Path("venv").exists():
        print("❌ Virtual environment not found. Please run install.py first.")
        return False

    if not Path(".env").exists():
        print(
            "❌ Environment file not found. Please copy .env.example to .env and configure it."
        )
        return False

    return True


def start_backend():
    """Start the backend server."""
    print("🚀 Starting KDP Strategist backend server...")
    try:
        subprocess.run([sys.executable, "run_server.py"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start backend: {e}")
        return False
    return True


def start_frontend():
    """Start the frontend development server."""
    print("🚀 Starting frontend development server...")
    frontend_dir = Path("frontend")

    if not frontend_dir.exists():
        print("❌ Frontend directory not found")
        return False

    # Check if node_modules exists
    if not (frontend_dir / "node_modules").exists():
        print("📦 Installing frontend dependencies...")
        try:
            subprocess.run(["npm", "install"], cwd=frontend_dir, check=True, shell=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install dependencies: {e}")
            return False

    try:
        print("📍 Frontend will start at: http://localhost:3000")
        subprocess.run(["npm", "start"], cwd=frontend_dir, check=True, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start frontend: {e}")
        return False
    return True


def start_interactive():
    """Start interactive mode."""
    print("🚀 Starting KDP Strategist in interactive mode...")
    try:
        subprocess.run(
            [sys.executable, "-m", "kdp_strategist", "--interactive"], check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start interactive mode: {e}")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Start KDP Strategist")
    parser.add_argument(
        "mode",
        choices=["backend", "frontend", "interactive", "full"],
        default="backend",
        nargs="?",
        help="Mode to start (default: backend)",
    )
    parser.add_argument(
        "--skip-checks", action="store_true", help="Skip environment checks"
    )

    args = parser.parse_args()

    # Check environment unless skipped
    if not args.skip_checks and not check_environment():
        print("\n💡 Run 'python install.py' to set up the environment")
        sys.exit(1)

    print(f"Starting KDP Strategist in {args.mode} mode...")

    if args.mode == "backend":
        success = start_backend()
    elif args.mode == "frontend":
        success = start_frontend()
    elif args.mode == "interactive":
        success = start_interactive()
    elif args.mode == "full":
        print("🚀 Starting full stack (backend + frontend)")
        print("Note: Start backend first, then frontend in a separate terminal")
        success = start_backend()
    else:
        print(f"❌ Unknown mode: {args.mode}")
        success = False

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()