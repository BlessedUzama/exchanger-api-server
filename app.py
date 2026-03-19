import os
import requests
import psycopg2
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
# CORS allows your frontend (e.g., Vercel) to fetch data from this Render server
CORS(app)

def get_db_connection():
    """Helper function to connect to Aiven PostgreSQL."""
    return psycopg2.connect(os.environ.get('DATABASE_URL'))

def init_db():
    """Creates the table if it doesn't exist (bypasses Aiven UI errors)."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fx_history (
            id SERIAL PRIMARY KEY,
            currency TEXT NOT NULL,
            rate FLOAT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.route('/')
def home():
    return "FX Sentinel Server is running. Use /check-rates to update or /api/history/all to fetch data."

@app.route('/check-rates')
def check_rates():
    """Triggered by Cron-job.org every hour."""
    init_db() # Ensure table exists
    
    # 1. Fetch current rate (using a reliable free API)
    api_url = "https://open.er-api.com/v6/latest/USD"
    try:
        data = requests.get(api_url).json()
        current_rate = data['rates']['EUR']
    except Exception as e:
        return f"API Error: {str(e)}", 500

    conn = get_db_connection()
    cur = conn.cursor()

    # 2. Get the most recent saved rate for cross-checking
    cur.execute("SELECT rate FROM fx_history ORDER BY timestamp DESC LIMIT 1;")
    row = cur.fetchone()
    last_rate = row[0] if row else current_rate

    # 3. Save the new rate to the database
    cur.execute("INSERT INTO fx_history (currency, rate) VALUES (%s, %s)", ('EUR', current_rate))
    conn.commit()
    
    cur.close()
    conn.close()

    return jsonify({
        "status": "success",
        "current_rate": current_rate,
        "previous_rate": last_rate,
        "difference": current_rate - last_rate
    })

@app.route('/api/history/all')
def get_all_history():
    """Returns every single rate in the database for your website's chart."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Select all data ordered chronologically
    cur.execute("SELECT rate, timestamp FROM fx_history ORDER BY timestamp ASC;")
    rows = cur.fetchall()
    
    # Format for Frontend (JSON)
    history = [
        {
            "rate": row[0], 
            "time": row[1].strftime('%H:%M'),
            "date": row[1].strftime('%Y-%m-%d')
        } for row in rows
    ]
    
    cur.close()
    conn.close()
    return jsonify(history)

if __name__ == "__main__":
    # Render requires port 10000
    app.run(host='0.0.0.0', port=10000)