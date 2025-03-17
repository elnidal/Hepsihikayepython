#!/usr/bin/env python3
"""
Load environment variables from .env file.
Run this script before running any other scripts that need environment variables.
Usage: source $(python load_env.py)
"""

import os

def load_dotenv():
    """Load environment variables from .env file."""
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    
    if not os.path.exists(env_file):
        print(f"Error: .env file not found at {env_file}")
        return
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            key, value = line.split('=', 1)
            # Print in a format that can be evaluated by the shell
            print(f"export {key}='{value}'")

if __name__ == "__main__":
    load_dotenv() 