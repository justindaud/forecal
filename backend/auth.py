#!/usr/bin/env python3
"""
Simple Authentication Module - No Database Required
Uses JWT tokens with hardcoded users for simplicity
"""

import jwt
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
import os

# Hardcoded users (in production, use environment variables)
USERS = {
    "salma": {
        "password": "justinkeren",  # In production, use hashed passwords
        "role": "Sales Executive",
        "name": "Salma"
    },
    "user": {
        "password": "user123",
        "role": "user", 
        "name": "Regular User"
    },
    "demo": {
        "password": "demo123",
        "role": "user",
        "name": "Demo User"
    }
}

# JWT Secret (in production, use environment variable)
JWT_SECRET = os.getenv('JWT_SECRET', 'revenue_management_jwt_secret_key_2024')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 200

def hash_password(password: str) -> str:
    """Simple password hashing (use bcrypt in production)"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == hashed

def generate_token(user_id: str, user_data: dict) -> str:
    """Generate JWT token for user"""
    payload = {
        'user_id': user_id,
        'name': user_data['name'],
        'role': user_data['role'],
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> dict:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def authenticate_user(username: str, password: str) -> dict:
    """Authenticate user with username/password"""
    if username not in USERS:
        return None
    
    user = USERS[username]
    if user['password'] == password:  # Simple comparison for demo
        return {
            'user_id': username,
            'name': user['name'],
            'role': user['role']
        }
    return None

def login_required(f):
    """Decorator to require authentication for Flask routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Check for token in Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        # Check for token in cookies
        if not token:
            token = request.cookies.get('auth_token')
        
        if not token:
            return jsonify({'error': 'Authentication required'}), 401
        
        try:
            payload = verify_token(token)
            if payload is None:
                return jsonify({'error': 'Invalid or expired token'}), 401
            
            # Add user info to request context
            request.current_user = payload
            return f(*args, **kwargs)
            
        except Exception as e:
            return jsonify({'error': 'Token verification failed'}), 401
    
    return decorated_function

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(request, 'current_user') or request.current_user.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    
    return decorated_function

def get_current_user():
    """Get current user from request context"""
    return getattr(request, 'current_user', None)
