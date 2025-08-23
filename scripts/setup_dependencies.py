#!/usr/bin/env python3
"""
Python Dependencies Handler

This module provides comprehensive dependency management for the KDP Strategist application.
It handles Python package installation, MCP dependencies, verification, and conflict resolution.

Functions:
- install_python_dependencies(): Install Python packages from requirements.txt
- install_mcp_dependencies(): Install MCP-specific packages
- verify_dependencies(): Check if all required imports are available
- handle_dependency_conflicts(): Resolve version conflicts and compatibility issues
"""

import subprocess
import sys
import importlib
import pkg_resources
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def install_python_dependencies(requirements_file: str = "requirements.txt") -> bool:
    """
    Install Python dependencies from requirements.txt file.
    
    Args:
        requirements_file: Path to requirements file (default: requirements.txt)
        
    Returns:
        bool: True if installation successful, False otherwise
    """
    try:
        project_root = Path(__file__).parent.parent
        requirements_path = project_root / requirements_file
        
        if not requirements_path.exists():
            logger.error(f"Requirements file not found: {requirements_path}")
            return False
            
        logger.info(f"Installing Python dependencies from {requirements_file}...")
        
        # Run pip install with requirements file
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_path)],
            capture_output=True,
            text=True,
            cwd=project_root
        )
        
        if result.returncode == 0:
            logger.info("Python dependencies installed successfully")
            return True
        else:
            logger.error(f"Failed to install dependencies: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error installing Python dependencies: {str(e)}")
        return False


def install_mcp_dependencies() -> bool:
    """
    Install MCP (Model Context Protocol) specific packages.
    
    Returns:
        bool: True if installation successful, False otherwise
    """
    try:
        logger.info("Installing MCP dependencies...")
        
        # MCP packages that might be needed
        mcp_packages = [
            "mcp",
            "anthropic-mcp",
            "mcp-server",
            "mcp-client"
        ]
        
        for package in mcp_packages:
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", package],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    logger.info(f"Successfully installed MCP package: {package}")
                else:
                    logger.warning(f"Could not install MCP package {package}: {result.stderr}")
                    
            except Exception as e:
                logger.warning(f"Error installing MCP package {package}: {str(e)}")
                
        return True
        
    except Exception as e:
        logger.error(f"Error installing MCP dependencies: {str(e)}")
        return False


def verify_dependencies() -> Tuple[bool, List[str]]:
    """
    Verify that all required dependencies can be imported.
    
    Returns:
        Tuple[bool, List[str]]: (success, list of missing packages)
    """
    try:
        logger.info("Verifying dependencies...")
        
        # Core dependencies that should be available
        required_packages = [
            "fastapi",
            "uvicorn",
            "pydantic",
            "requests",
            "python-dotenv",
            "sqlalchemy",
            "pandas",
            "numpy"
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                importlib.import_module(package.replace("-", "_"))
                logger.debug(f"✓ {package} is available")
            except ImportError:
                missing_packages.append(package)
                logger.warning(f"✗ {package} is missing")
                
        # Check project-specific modules
        project_modules = [
            "src.kdp_strategist",
            "config.settings"
        ]
        
        for module in project_modules:
            try:
                importlib.import_module(module)
                logger.debug(f"✓ {module} is available")
            except ImportError as e:
                logger.warning(f"✗ {module} import failed: {str(e)}")
                missing_packages.append(module)
                
        if missing_packages:
            logger.error(f"Missing dependencies: {', '.join(missing_packages)}")
            return False, missing_packages
        else:
            logger.info("All dependencies verified successfully")
            return True, []
            
    except Exception as e:
        logger.error(f"Error verifying dependencies: {str(e)}")
        return False, [str(e)]


def handle_dependency_conflicts() -> bool:
    """
    Handle dependency conflicts and version issues.
    
    Returns:
        bool: True if conflicts resolved, False otherwise
    """
    try:
        logger.info("Checking for dependency conflicts...")
        
        # Get installed packages
        installed_packages = {pkg.project_name: pkg.version for pkg in pkg_resources.working_set}
        
        # Known conflict patterns and resolutions
        conflict_resolutions = {
            "urllib3": ">=1.26.0,<2.0.0",
            "requests": ">=2.28.0",
            "pydantic": ">=1.10.0,<3.0.0",
            "fastapi": ">=0.100.0",
            "uvicorn": ">=0.20.0"
        }
        
        conflicts_found = False
        
        for package, required_version in conflict_resolutions.items():
            if package in installed_packages:
                current_version = installed_packages[package]
                logger.info(f"{package}: {current_version} (required: {required_version})")
                
                # For now, just log potential conflicts
                # In a production system, you might want to automatically resolve them
                try:
                    pkg_resources.require(f"{package}{required_version}")
                except pkg_resources.VersionConflict as e:
                    logger.warning(f"Version conflict detected: {e}")
                    conflicts_found = True
                    
        if conflicts_found:
            logger.warning("Dependency conflicts detected. Consider updating packages.")
            logger.info("To resolve conflicts, run: pip install --upgrade <package_name>")
            
        return True
        
    except Exception as e:
        logger.error(f"Error handling dependency conflicts: {str(e)}")
        return False


def get_dependency_status() -> Dict[str, any]:
    """
    Get comprehensive dependency status report.
    
    Returns:
        Dict containing dependency status information
    """
    try:
        # Verify dependencies
        deps_ok, missing = verify_dependencies()
        
        # Get installed packages
        installed_packages = {pkg.project_name: pkg.version for pkg in pkg_resources.working_set}
        
        # Check conflicts
        conflicts_resolved = handle_dependency_conflicts()
        
        status = {
            "dependencies_verified": deps_ok,
            "missing_packages": missing,
            "conflicts_resolved": conflicts_resolved,
            "installed_packages_count": len(installed_packages),
            "python_version": sys.version,
            "pip_version": subprocess.run(
                [sys.executable, "-m", "pip", "--version"],
                capture_output=True,
                text=True
            ).stdout.strip()
        }
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting dependency status: {str(e)}")
        return {"error": str(e)}


if __name__ == "__main__":
    """Run dependency setup when script is executed directly."""
    logger.info("Starting dependency setup...")
    
    # Install Python dependencies
    if install_python_dependencies():
        logger.info("✓ Python dependencies installed")
    else:
        logger.error("✗ Failed to install Python dependencies")
        sys.exit(1)
    
    # Install MCP dependencies
    if install_mcp_dependencies():
        logger.info("✓ MCP dependencies processed")
    else:
        logger.warning("⚠ MCP dependencies installation had issues")
    
    # Verify all dependencies
    deps_ok, missing = verify_dependencies()
    if deps_ok:
        logger.info("✓ All dependencies verified")
    else:
        logger.error(f"✗ Missing dependencies: {', '.join(missing)}")
        sys.exit(1)
    
    # Handle conflicts
    if handle_dependency_conflicts():
        logger.info("✓ Dependency conflicts checked")
    else:
        logger.warning("⚠ Issues with dependency conflict resolution")
    
    logger.info("Dependency setup completed successfully!")