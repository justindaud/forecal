#!/usr/bin/env python3
"""
Revenue Management Web Application - Flask Backend
Real-time pricing recommendations with date picker and calendar view
ORGANIZED BACKEND STRUCTURE VERSION
"""

from flask import Flask, render_template, request, jsonify, make_response
from flask_cors import CORS
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
import json
import os
from dotenv import load_dotenv
import sqlalchemy
from sqlalchemy import create_engine, text
import logging
import sys

# Add parent directory to path to import auth module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from auth import authenticate_user, generate_token, verify_token, login_required, admin_required, get_current_user

# Custom JSON encoder to handle NaN values
class NanSafeJSONEncoder(json.JSONEncoder):
    def encode(self, obj):
        if isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
            return 'null'
        return super().encode(obj)
    
    def iterencode(self, obj, _one_shot=False):
        if isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
            yield 'null'
        elif isinstance(obj, dict):
            yield '{'
            first = True
            for key, value in obj.items():
                if not first:
                    yield ','
                first = False
                yield json.dumps(key)
                yield ':'
                if isinstance(value, float) and (np.isnan(value) or np.isinf(value)):
                    yield 'null'
                else:
                    yield from self.iterencode(value, True)
            yield '}'
        elif isinstance(obj, list):
            yield '['
            first = True
            for item in obj:
                if not first:
                    yield ','
                first = False
                if isinstance(item, float) and (np.isnan(item) or np.isinf(item)):
                    yield 'null'
                else:
                    yield from self.iterencode(item, True)
            yield ']'
        else:
            yield from super().iterencode(obj, _one_shot)

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = 'revenue_management_secret_key'
app.json_encoder = NanSafeJSONEncoder

# Enable CORS for Next.js frontend with credentials
frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
CORS(app, origins=[frontend_url], supports_credentials=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RevenueManager:
    def __init__(self):
        self.data_cache = {}
        self.last_refresh = None
        
        # Set absolute paths for data and scripts
        self.backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.backend_root, 'data')
        self.scripts_dir = os.path.join(self.backend_root, 'scripts')

        
    def connect_db(self):
        """Connect to PostgreSQL database"""
        try:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                raise RuntimeError("DATABASE_URL not found in environment variables")
            
            engine = create_engine(database_url)
            return engine
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return None
    
    def refresh_data(self):
        """Refresh data from database and recalculate forecasts"""
        try:
            logger.info("Starting data refresh...")
            
            # Run data extraction (ABSOLUTE PATHS)
            os.system(f"cd {self.backend_root} && python3 scripts/data_extraction.py")
            
            # Run forecasting (ABSOLUTE PATHS)
            os.system(f"cd {self.backend_root} && python3 scripts/forecast.py")
            
            # Run enhanced forecasting (ABSOLUTE PATHS)
            os.system(f"cd {self.backend_root} && python3 scripts/fix_transparency.py")
            
            # Load refreshed data
            self.load_cached_data()
            self.last_refresh = datetime.now()
            
            logger.info("Data refresh completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Data refresh failed: {e}")
            return False
    
    def load_cached_data(self):
        """Load processed data from CSV files (UPDATED PATHS)"""
        try:
            # Load main dataset (FROM DATA FOLDER - ABSOLUTE PATH)
            dataset_path = os.path.join(self.data_dir, "dataset_processed.csv")
            if os.path.exists(dataset_path):
                self.data_cache['dataset'] = pd.read_csv(dataset_path)
                self.data_cache['dataset']['Date'] = pd.to_datetime(self.data_cache['dataset']['Date'])
            
            # (Deprecated) Skipping enhanced/predictions CSV loads; using combined_df.csv exclusively

            # Load combined notebook-aligned output for fast serving
            combined_path = os.path.join(self.data_dir, "combined_df.csv")
            if os.path.exists(combined_path):
                self.data_cache['combined'] = pd.read_csv(combined_path)
                self.data_cache['combined']['Date'] = pd.to_datetime(self.data_cache['combined']['Date'])
                logger.info("Loaded combined_df.csv")

            # Load holidays (FROM DATA FOLDER - ABSOLUTE PATH)
            holidays_path = os.path.join(self.data_dir, "holidays_info.csv")
            if os.path.exists(holidays_path):
                holidays_df = pd.read_csv(holidays_path)
                holidays_df['Date'] = pd.to_datetime(holidays_df['Date'])
                self.holidays_cache = holidays_df
                logger.info(f"Loaded holidays: {len(holidays_df)} records")
            
            logger.info("Data loaded successfully from organized backend structure")
            
        except Exception as e:
            logger.error(f"Failed to load cached data: {e}")

    def _clean_for_json(self, data):
        """Recursively clean data structure for JSON serialization"""
        if isinstance(data, dict):
            return {k: self._clean_for_json(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._clean_for_json(item) for item in data]
        elif isinstance(data, float) and (np.isnan(data) or np.isinf(data)):
            return None
        else:
            return data

    
    def get_pricing_recommendation(self, start_date, end_date, room_type=None):
        """Get pricing recommendations for date range"""
        try:
            if ('combined' not in self.data_cache or self.data_cache['combined'].empty) and ('forecast' not in self.data_cache or self.data_cache['forecast'].empty):
                self.load_cached_data()
            
            # Choose data source: prefer combined_df, else previous merge logic
            if 'combined' in self.data_cache and not self.data_cache['combined'].empty:
                forecast_data = self.data_cache['combined'].copy()
            else:
                has_pred = 'predictions' in self.data_cache and not self.data_cache['predictions'].empty
                has_fore = 'forecast' in self.data_cache and not self.data_cache['forecast'].empty
                forecast_data = None
                if has_pred and has_fore:
                    preds = self.data_cache['predictions'].copy()
                    forec = self.data_cache['forecast'].copy()
                    preds['__source_priority'] = 0
                    forec['__source_priority'] = 1
                    if 'Room Type' not in forec.columns and 'room_type' in forec.columns:
                        forec['Room Type'] = forec['room_type']
                    combined = pd.concat([preds, forec], ignore_index=True, sort=False)
                    combined['Date'] = pd.to_datetime(combined['Date'])
                    combined = combined.sort_values(['Date', 'Room Type', 'Arrangement', '__source_priority'])
                    combined = combined.drop_duplicates(subset=['Date', 'Room Type', 'Arrangement'], keep='first')
                    forecast_data = combined.drop(columns=['__source_priority'])
                elif has_pred:
                    forecast_data = self.data_cache['predictions'].copy()
                else:
                    forecast_data = self.data_cache['forecast'].copy()
            
            # Filter by date range
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            
            filtered_data = forecast_data[
                (forecast_data['Date'] >= start_dt) & 
                (forecast_data['Date'] <= end_dt)
            ].copy()
            
            # Filter by room type if specified
            if room_type and room_type != 'All':
                filtered_data = filtered_data[filtered_data['Room Type'] == room_type]
            
            if filtered_data.empty:
                return []
            
            # If using predictions.csv, these flags already exist; otherwise enrich from holidays
            if self.holidays_cache is not None:
                national_joint_holidays = set(self.holidays_cache[
                    self.holidays_cache['Kind'].isin(['national', 'joint'])
                ]['Date'].dt.date)
                school_holidays = set(self.holidays_cache[
                    self.holidays_cache['Kind'] == 'school'
                ]['Date'].dt.date)
                events = set(self.holidays_cache[
                    self.holidays_cache['Kind'] == 'event'
                ]['Date'].dt.date)
                fasting_days = set(self.holidays_cache[
                    self.holidays_cache['Kind'] == 'fasting'
                ]['Date'].dt.date)
                if 'Is_Holiday' not in filtered_data.columns:
                    filtered_data['Is_Holiday'] = filtered_data['Date'].dt.date.isin(national_joint_holidays)
                if 'Is_SchoolHoliday' not in filtered_data.columns:
                    filtered_data['Is_SchoolHoliday'] = filtered_data['Date'].dt.date.isin(school_holidays)
                if 'Is_Event' not in filtered_data.columns:
                    filtered_data['Is_Event'] = filtered_data['Date'].dt.date.isin(events)
                # Add fasting flag and exclude from holiday
                filtered_data['Is_Fasting'] = filtered_data['Date'].dt.date.isin(fasting_days)
                filtered_data.loc[filtered_data['Is_Fasting'] == True, 'Is_Holiday'] = False

            # Attach holiday details map (name, kind) if available
            holiday_details_map = {}
            if getattr(self, 'holidays_cache', None) is not None:
                for _, hrow in self.holidays_cache.iterrows():
                    holiday_details_map[hrow['Date'].date()] = {
                        'name': hrow.get('Description', ''),
                        'kind': hrow.get('Kind', '')
                    }

            
            # Coerce ARR
            if 'Average Room Rate' in filtered_data.columns:
                filtered_data['Average Room Rate'] = pd.to_numeric(filtered_data['Average Room Rate'], errors='coerce')
            
            # Robust occupancy derivation into __occ
            filtered_data['__occ'] = np.nan
            if 'Occupancy Rate' in filtered_data.columns:
                if filtered_data['Occupancy Rate'].dtype == object:
                    def _parse_occ_str(x):
                        try:
                            s = str(x).strip()
                            if s.endswith('%'):
                                return float(s.replace('%',''))/100.0
                            val = float(s)
                            return val/100.0 if val > 1.0 else val
                        except Exception:
                            return np.nan
                    filtered_data['__occ'] = filtered_data['Occupancy Rate'].apply(_parse_occ_str)
                else:
                    # Numeric occupancy; normalize if >1 (assume percentage)
                    occ_num = pd.to_numeric(filtered_data['Occupancy Rate'], errors='coerce')
                    filtered_data['__occ'] = occ_num.where(occ_num <= 1.0, occ_num/100.0)

            # Fill from alternate columns if still NaN
            if '__occ' in filtered_data.columns and '__occ' in filtered_data:
                if 'Occ' in filtered_data.columns:
                    alt = pd.to_numeric(filtered_data['Occ'], errors='coerce')
                    filtered_data['__occ'] = filtered_data['__occ'].fillna(alt)
                if 'Predicted_Occupancy' in filtered_data.columns:
                    alt2 = pd.to_numeric(filtered_data['Predicted_Occupancy'], errors='coerce')
                    filtered_data['__occ'] = filtered_data['__occ'].fillna(alt2)

            # Ensure minimal derived fields if not present (predictions.csv already includes numeric day fields)
            if 'Day_of_Week' not in filtered_data.columns:
                filtered_data['Day_of_Week'] = filtered_data['Date'].dt.day_name()
            if 'Is_Weekend' not in filtered_data.columns:
                filtered_data['Is_Weekend'] = filtered_data['Date'].dt.weekday.isin([5, 6])
            
            # Calculate recommendations
            recommendations = []
            
            for _, row in filtered_data.iterrows():
                # Use values directly from selected source (combined_df preferred)
                recommended_arr = row.get('Average Room Rate', np.nan)
                occ_val = row.get('__occ', np.nan)
                if pd.isna(occ_val):
                    occ_val = row.get('Occ', np.nan)
                recommended_arr = max(0, float(recommended_arr) if not pd.isna(recommended_arr) else 0)
                recommended_occ = max(0, min(1, float(occ_val) if not pd.isna(occ_val) else 0))
                
                recommendation = {
                    'date': row['Date'].strftime('%Y-%m-%d'),
                    'room_type': str(row['Room Type']),
                    'arrangement': str(row.get('Arrangement')) if 'Arrangement' in row.index and not pd.isna(row.get('Arrangement')) else None,
                    'recommended_arr': float(recommended_arr) if not pd.isna(recommended_arr) else 0.0,
                    'recommended_occupancy': float(recommended_occ) if not pd.isna(recommended_occ) else 0.0,
                    'is_holiday': bool(row['Is_Holiday']) if not pd.isna(row['Is_Holiday']) else False,
                    'is_school_holiday': bool(row.get('Is_SchoolHoliday', False)) if not pd.isna(row.get('Is_SchoolHoliday', False)) else False,
                    'is_event': bool(row.get('Is_Event', False)) if not pd.isna(row.get('Is_Event', False)) else False,
                    'is_weekend': bool(row['Is_Weekend']) if not pd.isna(row['Is_Weekend']) else False,
                    'day_of_week': str(row['Day_of_Week']) if not pd.isna(row['Day_of_Week']) else 'Unknown',
                    'is_fasting': bool(row.get('Is_Fasting', False)) if not pd.isna(row.get('Is_Fasting', False)) else False,
                    # Transparent driver fields when available
                    'is_bridge': bool(row.get('Is_Bridge', False)),
                    'holiday_duration': int(row.get('Holiday_Duration', 0)) if not pd.isna(row.get('Holiday_Duration', 0)) else 0,
                    'days_of_holiday': int(row.get('Days_of_Holiday', 0)) if not pd.isna(row.get('Days_of_Holiday', 0)) else 0,
                    'distance_to_holiday': int(row.get('Distance_to_Holiday', 0)) if not pd.isna(row.get('Distance_to_Holiday', 0)) else 0,
                    'holiday_details': holiday_details_map.get(row['Date'].date()) if hasattr(row['Date'], 'date') else None,
                }
                
                recommendations.append(recommendation)
            
            # Clean recommendations for JSON
            cleaned_recommendations = self._clean_for_json(recommendations)
            return cleaned_recommendations
            
        except Exception as e:
            logger.error(f"Failed to get pricing recommendations: {e}")
            return []
    
    # Removed obsolete helper methods (confidence/considerations/holiday category)
    
    def get_calendar_data(self, year, month):
        """Get calendar data for a specific month"""
        try:
            # Create date range for the month
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1) - timedelta(days=1)
            
            # Get recommendations for the month
            recommendations = self.get_pricing_recommendation(
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            
            # Organize by date
            calendar_data = {}
            for rec in recommendations:
                date_str = rec['date']
                if date_str not in calendar_data:
                    calendar_data[date_str] = []
                calendar_data[date_str].append(rec)
            
            # Clean calendar data for JSON serialization
            cleaned_calendar_data = self._clean_for_json(calendar_data)
            return cleaned_calendar_data
            
        except Exception as e:
            logger.error(f"Failed to get calendar data: {e}")
            return {}

# Initialize revenue manager
revenue_manager = RevenueManager()

@app.route('/')
def index():
    return jsonify({"message": "Revenue Management API", "status": "running", "structure": "organized_backend"})

@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    """Refresh data from database"""
    success = revenue_manager.refresh_data()
    return jsonify({
        'success': success,
        'message': 'Data refreshed successfully' if success else 'Data refresh failed'
    })

@app.route('/api/recommendations', methods=['GET'])
def get_recommendations():
    """Get pricing recommendations for date range"""
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    room_type = request.args.get('room_type', 'All')
    
    if not start_date or not end_date:
        return jsonify({'error': 'start_date and end_date are required'}), 400
    
    recommendations = revenue_manager.get_pricing_recommendation(start_date, end_date, room_type)
    
    return jsonify({
        'recommendations': recommendations,
        'count': len(recommendations),
        'date_range': f"{start_date} to {end_date}",
        'room_type': room_type
    })

@app.route('/api/calendar/<int:year>/<int:month>')
@login_required
def get_calendar(year, month):
    """Get calendar data for specific month"""
    calendar_data = revenue_manager.get_calendar_data(year, month)
    return jsonify(calendar_data)

# Authentication routes
@app.route('/api/auth/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        user = authenticate_user(username, password)
        if not user:
            return jsonify({'error': 'Invalid credentials'}), 401
        
        token = generate_token(user['user_id'], user)
        
        response = make_response(jsonify({
            'message': 'Login successful',
            'user': {
                'user_id': user['user_id'],
                'name': user['name'],
                'role': user['role']
            }
        }))
        
        # Set HTTP-only cookie
        response.set_cookie(
            'auth_token',
            token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite='Lax',
            max_age=24*60*60  # 24 hours
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """User logout endpoint"""
    response = make_response(jsonify({'message': 'Logout successful'}))
    response.set_cookie('auth_token', '', expires=0)
    return response

@app.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user_info():
    """Get current user information"""
    user = get_current_user()
    return jsonify({
        'user_id': user['user_id'],
        'name': user['name'],
        'role': user['role']
    })

@app.route('/api/room_types')
@login_required
def get_room_types():
    """Get available room types"""
    room_types = ['Deluxe', 'Executive Suite', 'Suite', 'Family Suite']
    return jsonify({'room_types': room_types})

if __name__ == "__main__":
    print("=== REVENUE MANAGEMENT BACKEND (ORGANIZED STRUCTURE) ===")
    print("Loading data from organized backend/data/ folder...")
    revenue_manager.load_cached_data()
    port = int(os.getenv('PORT', 5001))
    print(f"API available at: http://localhost:{port}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=True)
