#!/usr/bin/env python3
"""
Database migration script for Schoova
Adds password_hash column to existing users table
"""

import sqlite3
import os

def migrate_database():
    """Migrate the database to add password_hash column"""
    db_path = 'accountability.db'
    
    if not os.path.exists(db_path):
        print("Database doesn't exist. Run the app first to create it.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if password_hash column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'password_hash' in columns:
            print("password_hash column already exists. No migration needed.")
            return
        
        print("Adding password_hash column to users table...")
        
        # Add the password_hash column
        cursor.execute('ALTER TABLE users ADD COLUMN password_hash TEXT')
        
        # Update existing users with a default password hash (they'll need to reset)
        cursor.execute('UPDATE users SET password_hash = ? WHERE password_hash IS NULL', 
                      ('default:needs_reset',))
        
        conn.commit()
        print("✅ Database migration completed successfully!")
        print("Note: Existing users will need to reset their passwords.")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
