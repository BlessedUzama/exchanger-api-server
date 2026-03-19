import os
import requests
import psycopg2
from flask import Flask

app = Flask(__name__)

# Connect to your Aiven Database
def get_db_connection():
    return psycopg2.connect(os.environ.get('DATABASE_URL'))

@app.route('/check-rates')
def check_rates():
    # 1. Fetch current rate
    api_url = "https://open.er-api.com/v6/latest/USD"
    data = requests.get(api_url).json()
    current_rate = data['rates']['EUR']

    conn = get_db_connection()
    cur = conn.cursor()

    # 2. Get the last saved rate
    cur.execute("SELECT rate FROM fx_history ORDER BY timestamp DESC LIMIT 1;")
    row = cur.fetchone()
    last_rate = row[0] if row else current_rate

    # 3. Cross-check logic
    diff = current_rate - last_rate
    percent_change = (diff / last_rate) * 100

    message = f"Current: {current_rate}, Previous: {last_rate}. Change: {percent_change:.2f}%"
    
    # 4. If change is > 0.5%, you could trigger an email here
    if abs(percent_change) > 0.5:
        print(f"ALERT: {message}")

    # 5. Save the new rate
    cur.execute("INSERT INTO fx_history (currency, rate) VALUES (%s, %s)", ('EUR', current_rate))
    conn.commit()
    cur.close()
    conn.close()

    return message, 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)