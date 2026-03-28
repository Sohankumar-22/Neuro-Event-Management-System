import sqlite3

def update_db():
    conn = sqlite3.connect('instance/database.db')
    cursor = conn.cursor()
    
    columns_to_add = [
        ("customer_name", "VARCHAR(150)"),
        ("contact_number", "VARCHAR(20)"),
        ("special_requirements", "TEXT"),
        ("event_extra", "VARCHAR(255)"),
        ("payment_method", "VARCHAR(50)"),
        ("price", "FLOAT DEFAULT 0.0"),
        ("payment_status", "VARCHAR(20) DEFAULT 'Pending'"),
        ("feedback_sent", "BOOLEAN DEFAULT False")
    ]
    
    table_name = "booking"
    
    # Check existing columns
    cursor.execute(f"PRAGMA table_info({table_name})")
    existing_columns = [info[1] for info in cursor.fetchall()]
    
    print(f"Existing columns in '{table_name}': {existing_columns}")
    
    for col_name, col_type in columns_to_add:
        if col_name not in existing_columns:
            try:
                print(f"Adding column: {col_name} ({col_type})")
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
        else:
            print(f"Column '{col_name}' already exists.")
            
    conn.commit()
    conn.close()
    print("Database update complete.")

if __name__ == "__main__":
    update_db()
