import os
import requests
import psycopg2
from psycopg2.extras import Json # Required to save dictionaries to JSONB
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
# Allows your React app (Vite/Vercel) to call these APIs
CORS(app)

def get_db_connection():
    """Establishes connection to Aiven PostgreSQL."""
    return psycopg2.connect(os.environ.get('DATABASE_URL'))

def init_db():
    """
    Sets up the JSONB table. 
    NOTE: If you want to wipe old data and start fresh with the new 
    structure, uncomment the 'DROP TABLE' line for ONE deploy only.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    # cur.execute("DROP TABLE IF EXISTS fx_history CASCADE;") 
    cur.execute("""
        CREATE TABLE IF NOT EXISTS fx_history (
            id SERIAL PRIMARY KEY,
            rates JSONB NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.route('/')
def home():
    return "CURRENCY.IO Backend is Live. Endpoints: /check-rates, /api/history/previous, /api/history/all"

@app.route('/check-rates')
def check_rates():
    """Triggered by Cron-job.org every hour to save global market state."""
    init_db()
    api_url = "https://open.er-api.com/v6/latest/USD"
    
    try:
        response = requests.get(api_url)
        data = response.json()
        all_rates = data['rates'] # Captures all 100+ currencies
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    conn = get_db_connection()
    cur = conn.cursor()
    # Save the entire rates dictionary into one JSONB cell
    cur.execute("INSERT INTO fx_history (rates) VALUES (%s)", [Json(all_rates)])
    conn.commit()
    cur.close()
    conn.close()
    
    return jsonify({"status": "success", "count": len(all_rates)})

@app.route('/api/history/previous')
def get_previous_rates():
    """Returns the rates from the check BEFORE the most recent one for trend comparison."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # OFFSET 1 skips the latest entry to give you the previous historical baseline
    cur.execute("SELECT rates FROM fx_history ORDER BY timestamp DESC LIMIT 1 OFFSET 1;")
    row = cur.fetchone()
    
    cur.close()
    conn.close()
    
    if row:
        return jsonify(row[0])
    return jsonify({}) # Returns empty if database only has 1 entry

@app.route('/api/history/all')
def get_all_history():
    """Returns the full timeline of all saved rates for charts."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT rates, timestamp FROM fx_history ORDER BY timestamp ASC;")
    rows = cur.fetchall()
    
    history = [
        {
            "rates": row[0], 
            "time": row[1].strftime('%H:%M'),
            "date": row[1].strftime('%Y-%m-%d')
        } for row in rows
    ]
    
    cur.close()
    conn.close()
    return jsonify(history)

if __name__ == "__main__":
    # Render's default port is 10000
    app.run(host='0.0.0.0', port=10000)