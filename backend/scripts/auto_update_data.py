#!/usr/bin/env python3
"""
Auto Update Data Pipeline
Runs data extraction, forecasting, and notifies frontend
"""

import subprocess
import requests
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_data_pipeline():
    """Run complete data update pipeline"""
    
    print("=== STARTING AUTO DATA UPDATE PIPELINE ===")
    
    try:
        # Step 1: Data extraction
        print("1. Running data extraction...")
        result1 = subprocess.run(["python3", "data_extraction.py"], 
                               capture_output=True, text=True, check=True)
        print("✅ Data extraction completed")
        
        # Step 2: Unified Forecasting (includes daily variation and transparency)
        print("2. Running unified forecasting with transparency...")
        result2 = subprocess.run(["python3", "forecast.py"], 
                               capture_output=True, text=True, check=True)
        print("✅ Unified forecasting completed (core + enhanced + evaluation)")
        
        # Step 3: Notify backend to refresh cache
        print("3. Refreshing backend cache...")
        try:
            backend_url = os.getenv('BACKEND_URL', 'http://localhost:5001')
            response = requests.post(f"{backend_url}/api/refresh", timeout=30)
            if response.status_code == 200:
                print("✅ Backend cache refreshed successfully")
            else:
                print(f"⚠️ Backend refresh returned status: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Backend refresh failed: {e}")
            print("💡 You may need to restart servers manually")
        
        print("\n🎯 DATA UPDATE PIPELINE COMPLETED!")
        print("Frontend should now show updated data")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Pipeline failed at step: {e.cmd}")
        print(f"Error: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = run_data_pipeline()
    if success:
        print("\n✅ All data updated successfully!")
    else:
        print("\n❌ Data update failed - check errors above")
