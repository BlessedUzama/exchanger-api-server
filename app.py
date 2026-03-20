import os
import requests
import psycopg2
from psycopg2.extras import Json
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def get_db_connection():
    return psycopg2.connect(os.environ.get('DATABASE_URL'))

@app.route('/check-rates')
def check_rates():
    api_url = "https://open.er-api.com/v6/latest/USD"
    try:
        data = requests.get(api_url).json()
        all_rates = data['rates']
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO fx_history (rates) VALUES (%s)", [Json(all_rates)])
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "success", "count": len(all_rates)})

@app.route('/api/history/previous')
def get_previous_rates():
    """Smart Fallback: Gets 2nd most recent, or 1st if only one exists."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Attempt to get the previous baseline (OFFSET 1)
    cur.execute("SELECT rates FROM fx_history ORDER BY timestamp DESC LIMIT 1 OFFSET 1;")
    row = cur.fetchone()
    
    # If database is fresh and only has 1 entry, fallback to that 1 entry
    if not row:
        cur.execute("SELECT rates FROM fx_history ORDER BY timestamp DESC LIMIT 1;")
        row = cur.fetchone()
    
    cur.close()
    conn.close()
    return jsonify(row[0] if row else {})

@app.route('/api/history/all')
def get_all_history():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT rates, timestamp FROM fx_history ORDER BY timestamp ASC;")
    rows = cur.fetchall()
    history = [{"rates": row[0], "time": row[1].strftime('%H:%M')} for row in rows]
    cur.close()
    conn.close()
    return jsonify(history)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)