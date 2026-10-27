import sqlite3
import os

db_path = 'help_desk.db'

if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # إضافة العمود الجديد
        cursor.execute("ALTER TABLE user ADD COLUMN last_work_date DATE")
        
        conn.commit()
        conn.close()
        print("Successfully added last_work_date column to user table.")
    except Exception as e:
        print(f"Error: {e} (Column might already exist)")
else:
    print("Database file not found. It will be created with new schema on next app run.")
