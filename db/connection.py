import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT',5432)),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD') or None
        )
        return conn
    except Exception as e:
        print(f"Connection failed: {e}")
        return None

if __name__ == "__main__":
    conn = get_connection()
    if conn:
        print("Connection successful")
    else:
        print("Connection failed")