#!/usr/bin/env python3
import socket
import subprocess
import sys
import os
import time

def find_available_port(start_port=10001, max_attempts=10):
    """Find an available port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except socket.error:
                continue
    return None

def kill_existing_processes():
    """Kill any existing Flask app processes."""
    try:
        subprocess.run(['pkill', '-f', 'python3 app.py'], check=False)
        # Give processes time to terminate
        time.sleep(1)
    except Exception as e:
        print(f"Warning: Failed to kill existing processes: {e}")

def main():
    # Kill any existing Flask processes
    kill_existing_processes()
    
    # Find an available port
    port = find_available_port()
    if not port:
        print("Error: Could not find an available port after multiple attempts.")
        sys.exit(1)
    
    print(f"Starting Flask app on port {port}...")
    
    # Build the command to run the Flask app
    cmd = [sys.executable, 'app.py', '--port', str(port)]
    
    # Add debug flag if specified
    if '--debug' in sys.argv:
        cmd.append('--debug')
    
    try:
        # Execute the Flask app
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nShutting down the server...")
    except Exception as e:
        print(f"Error starting the server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 