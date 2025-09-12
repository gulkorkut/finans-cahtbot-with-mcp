#!/usr/bin/env python3
"""
Startup script for the Finance Bot servers
"""
import subprocess
import time
import sys
from pathlib import Path

def start_server(script_path, name, port):
    """Start a server in a subprocess"""
    print(f"Starting {name} on port {port}...")
    try:
        process = subprocess.Popen(
            [sys.executable, script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        print(f"✅ {name} started (PID: {process.pid})")
        return process
    except Exception as e:
        print(f"❌ Failed to start {name}: {e}")
        return None

def main():
    print("🚀 Starting Finance Bot servers...")
    
    # Get the current directory
    current_dir = Path(__file__).parent
    
    # Start servers
    servers = [
        ("Data Server", "data_servers/main.py", 8000),
        ("Translation Server", "translation_server.py", 8002),
        ("Money Server", "money_server.py", 8003),
        ("Product Server", "product_server.py", 8004),
        ("Fraud Server", "fraud_server.py", 8005),  # FraudAgent

    ]
    
    processes = []
    
    for name, script, port in servers:
        script_path = current_dir / script
        if not script_path.exists():
            print(f"❌ Script not found: {script_path}")
            continue
            
        process = start_server(script_path, name, port)
        if process:
            processes.append((name, process))
        time.sleep(2)  # Give each server time to start
    
    print("\n📋 Server Status:")
    for name, process in processes:
        status = "✅ Running" if process.poll() is None else "❌ Stopped"
        print(f"  {name}: {status}")
    
    print("\n⏳ Waiting for servers to be ready...")
    time.sleep(5)
    
    print("\n🎯 All servers started! You can now run:")
    print("  streamlit run app.py")
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
            # Check if any server has stopped
            for name, process in processes:
                if process.poll() is not None:
                    print(f"⚠️  {name} has stopped unexpectedly")
    except KeyboardInterrupt:
        print("\n🛑 Stopping all servers...")
        for name, process in processes:
            if process.poll() is None:
                process.terminate()
                print(f"  Stopped {name}")

if __name__ == "__main__":
    main() 