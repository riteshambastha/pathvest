#!/usr/bin/env python3
"""
Docker Verification Script for LEAN Integration

This script verifies that Docker is properly installed and running,
and checks if the LEAN Docker image can be pulled.

Usage:
    python verify_docker.py
"""

import subprocess
import sys
import time


def run_command(cmd, check=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=check
        )
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr


def check_docker_installed():
    """Check if Docker is installed."""
    print("🔍 Checking if Docker is installed...")
    success, stdout, stderr = run_command("docker --version", check=False)
    
    if success:
        print(f"✅ Docker is installed: {stdout}")
        return True
    else:
        print("❌ Docker is not installed or not in PATH")
        print("\nTo install Docker:")
        print("1. Download from: https://www.docker.com/products/docker-desktop/")
        print("2. Or run: brew install --cask docker")
        print("3. Start Docker Desktop and wait for it to fully start")
        return False


def check_docker_running():
    """Check if Docker daemon is running."""
    print("\n🔍 Checking if Docker daemon is running...")
    success, stdout, stderr = run_command("docker info", check=False)
    
    if success:
        print("✅ Docker daemon is running")
        return True
    else:
        print("❌ Docker daemon is not running")
        print("\nPlease start Docker Desktop:")
        print("1. Open Docker Desktop from Applications")
        print("2. Wait for the whale icon 🐳 to appear in the menu bar")
        print("3. Ensure the whale icon is not animated (means it's fully started)")
        return False


def check_docker_version():
    """Check Docker version and display info."""
    print("\n📊 Docker Information:")
    
    # Docker version
    success, stdout, _ = run_command("docker --version", check=False)
    if success:
        print(f"   Version: {stdout}")
    
    # Docker info
    success, stdout, _ = run_command("docker info --format '{{.ServerVersion}}'", check=False)
    if success:
        print(f"   Server Version: {stdout}")
    
    # Available images
    success, stdout, _ = run_command("docker images --format '{{.Repository}}:{{.Tag}}' | head -5", check=False)
    if success and stdout:
        print(f"   Local Images: {len(stdout.split())}")


def pull_lean_image():
    """Pull the LEAN Docker image."""
    print("\n🐳 Pulling LEAN Docker image...")
    print("   This may take a few minutes on first run...")
    
    # Use the official LEAN image
    image = "quantconnect/lean:latest"
    
    success, stdout, stderr = run_command(f"docker pull {image}", check=False)
    
    if success:
        print(f"✅ Successfully pulled {image}")
        return True
    else:
        print(f"❌ Failed to pull {image}")
        print(f"   Error: {stderr}")
        return False


def test_lean_container():
    """Test running a simple LEAN container."""
    print("\n🧪 Testing LEAN container...")
    
    # Run a simple test - just check if the container starts
    cmd = "docker run --rm quantconnect/lean:latest --help"
    success, stdout, stderr = run_command(cmd, check=False)
    
    if success or "usage" in stdout.lower() or "usage" in stderr.lower():
        print("✅ LEAN container can be started successfully")
        return True
    else:
        print("❌ Failed to start LEAN container")
        print(f"   Error: {stderr}")
        return False


def main():
    """Main verification workflow."""
    print("=" * 60)
    print("🚀 PathVest LEAN Docker Verification")
    print("=" * 60)
    
    # Step 1: Check if Docker is installed
    if not check_docker_installed():
        sys.exit(1)
    
    # Step 2: Check if Docker daemon is running
    if not check_docker_running():
        print("\n⏸️  Waiting for Docker to start...")
        print("   Please start Docker Desktop and run this script again.")
        sys.exit(1)
    
    # Step 3: Show Docker info
    check_docker_version()
    
    # Step 4: Pull LEAN image
    print("\n" + "=" * 60)
    user_input = input("Do you want to pull the LEAN Docker image? (y/n): ").strip().lower()
    
    if user_input == 'y':
        if not pull_lean_image():
            print("\n⚠️  Warning: Failed to pull LEAN image")
            print("   You can try again later with: docker pull quantconnect/lean:latest")
        else:
            # Step 5: Test LEAN container
            if test_lean_container():
                print("\n" + "=" * 60)
                print("🎉 SUCCESS! Docker and LEAN are ready!")
                print("=" * 60)
                print("\n✅ Next Steps:")
                print("   1. Run Phase 2 tests: python lean/tests/test_basic_backtest.py")
                print("   2. Continue with LEAN integration in lean_engine.py")
                print("   3. Start building custom SEC data sources")
            else:
                print("\n⚠️  Warning: LEAN container test failed")
                print("   This might be okay - some features require additional setup")
    else:
        print("\n✅ Docker verification complete!")
        print("   You can pull the LEAN image later with:")
        print("   docker pull quantconnect/lean:latest")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()

