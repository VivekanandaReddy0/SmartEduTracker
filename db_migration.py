import os
import sys
import psycopg2
from psycopg2 import sql
import subprocess
import time

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL')

def check_database_connection():
    """Check if the database is accessible"""
    conn = None
    try:
        print("Testing database connection...")
        if not DATABASE_URL:
            print("No DATABASE_URL environment variable found")
            return False
            
        # Try to connect
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Execute a simple query
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        if result and result[0] == 1:
            print("Database connection successful!")
            return True
        else:
            print("Database connection failed - unexpected response")
            return False
            
    except Exception as e:
        print(f"Database connection error: {e}")
        return False
    finally:
        if conn:
            conn.close()

def initialize_database():
    """Create schema and tables"""
    try:
        print("Initializing database schema...")
        
        # Just run the app initialization logic to create tables
        # This is simpler than maintaining separate SQL
        from app import create_app
        app = create_app()
        
        print("Database initialization completed!")
        return True
        
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False

def add_missing_columns():
    """Add missing columns to existing tables"""
    conn = None
    cursor = None
    
    try:
        # Connect to database
        print("Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Check if student table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'student'
            )
        """)
        
        if not cursor.fetchone()[0]:
            print("Student table doesn't exist yet - will be created by app")
            return True
            
        # Check if profile_photo column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='student' AND column_name='profile_photo'
        """)
        
        # Add profile_photo if it doesn't exist
        if cursor.fetchone() is None:
            print("Adding profile_photo column to student table...")
            cursor.execute(
                sql.SQL("ALTER TABLE student ADD COLUMN profile_photo BYTEA")
            )
            
        # Check if photo_mimetype column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='student' AND column_name='photo_mimetype'
        """)
        
        # Add photo_mimetype if it doesn't exist
        if cursor.fetchone() is None:
            print("Adding photo_mimetype column to student table...")
            cursor.execute(
                sql.SQL("ALTER TABLE student ADD COLUMN photo_mimetype VARCHAR(64)")
            )
        
        # List all tables in the database for debugging
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema='public'
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tables in database: {', '.join(tables)}")
            
        # Commit changes
        conn.commit()
        print("Database migration completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"Error during migration: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Starting database migration process...")
    
    # Check if DB connection works
    if not check_database_connection():
        print("Cannot proceed with migration - database connection failed")
        sys.exit(1)
    
    # Add missing columns to existing tables
    success = add_missing_columns()
    
    # Initialize database if needed
    if success:
        success = initialize_database()
    
    sys.exit(0 if success else 1)