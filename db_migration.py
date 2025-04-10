import os
import sys
import psycopg2
from psycopg2 import sql

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL')

def add_missing_columns():
    """Add missing columns to the student table"""
    try:
        # Connect to database
        print("Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
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
            
        # Commit changes
        conn.commit()
        print("Database migration completed successfully!")
        
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
    
    return True

if __name__ == "__main__":
    print("Starting database migration...")
    success = add_missing_columns()
    sys.exit(0 if success else 1)