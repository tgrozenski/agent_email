import asyncio
import asyncpg
import os

# Construct the path to the schema file relative to this script's location.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), 'sql', 'schema.sql')
DATABASE_URL = os.environ.get("DATABASE_URL")

async def initialize_database():
    """
    Connects to the database, drops existing tables (if any),
    and creates new tables based on the schema.sql file.
    """
    print("--- Starting Database Initialization ---")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
    except Exception as e:
        print(f"Failed to connect to the database: {e}")
        return

    try:
        with open(SCHEMA_PATH, 'r') as f:
            schema_sql = f.read()
        await conn.execute(schema_sql)
        
    except FileNotFoundError:
        print(f"Error: Schema file not found at {SCHEMA_PATH}")
    except Exception as e:
        print(f"An error occurred during schema creation: {e}")
    finally:
        await conn.close()
        print("--- Database Initialization Complete ---")

if __name__ == "__main__":
    asyncio.run(initialize_database())