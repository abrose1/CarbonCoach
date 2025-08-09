#!/usr/bin/env python3
"""
Database migration script for Railway deployment
"""
from app import create_app
from flask_migrate import upgrade

def run_migrations():
    """Run database migrations"""
    app = create_app()
    
    with app.app_context():
        try:
            # Run migrations
            upgrade()
            print("Database migrations completed successfully")
        except Exception as e:
            print(f"Migration error: {e}")
            # Don't fall back to create_all in production - we want to preserve data
            raise

if __name__ == "__main__":
    run_migrations()