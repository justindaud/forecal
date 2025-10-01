#!/usr/bin/env python3
"""
Revenue Management Backend - Main Entry Point
Start the Flask API server from the organized backend structure
"""

import sys
import os
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

# Import the Flask app
from app.revenue_management_app import app

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    print("=== STARTING REVENUE MANAGEMENT BACKEND ===")
    print("Backend structure: ORGANIZED ✅")
    print("=" * 50)
    
    port = int(os.getenv('PORT', 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
