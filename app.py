import os
import requests
import psycopg2
from flask import Flask

app = Flask(__name__)

def init_db():
    """This creates the table automatically if it doesn't exist."""
    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
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

@app.route('/check-rates')
def check_rates():
    init_db() # Run the check every time (or just once)
    
    api_url = "https://open.er-api.com/v6/latest/USD"
    data = requests.get(api_url).json()
    current_rate = data['rates']['EUR']

    conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
    cur = conn.cursor()

    # Get the last saved rate
    cur.execute("SELECT rate FROM fx_history ORDER BY timestamp DESC LIMIT 1;")
    row = cur.fetchone()
    last_rate = row[0] if row else current_rate

    # Calculate change
    diff = current_rate - last_rate
    
    # Save the new rate
    cur.execute("INSERT INTO fx_history (currency, rate) VALUES (%s, %s)", ('EUR', current_rate))
    conn.commit()
    cur.close()
    conn.close()

    return f"Done! Current EUR rate: {current_rate}. Previous: {last_rate}", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)