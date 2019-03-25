"""
Database initialization script. Should be executed on application startup.
"""

from app import db

db.create_all()
