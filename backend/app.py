# Flask server to fetch METAR data

from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
CORS(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/metar")
def get_metar():
    station = request.args.get("station").upper()
    url = f"https://aviationweather.gov/api/data/metar?ids={station}&format=json"

    try:
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()

        for report in data:
            obs_timestamp = report.get("obsTime")
            if obs_timestamp:
                try:
                    utc_time = datetime.fromtimestamp(obs_timestamp, tz=ZoneInfo("UTC"))
                    local_time = utc_time.astimezone(ZoneInfo("America/Los_Angeles"))
                    report["localObsTime"] = local_time.strftime("%Y-%m-%d %I:%M %p %Z")
                except Exception as e:
                    print("Error parsing obsTime:", obs_timestamp, e)
                    report["localObsTime"] = "Unknown"
            else:
                report["localObsTime"] = "Not provided"

        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    


DB_CONFIG = {
    'host': 'localhost',
    'port': '5432',
    'dbname': 'historic_METAR',
    'user': 'postgres',
    'password': 'yourpassword'
}
    
@app.route("/metar-history")
def metar_history():
    icao = request.args.get('icao').upper()
    if not icao:
        return jsonify([])

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        cur.execute("""
            SELECT observation_time, temperature_c, dewpoint_c, wind_dir_degrees, wind_speed_kt, visibility_statute_mi, elevation, cloud_cover, cloud_base
            FROM metar_reports
            WHERE station_id = %s
            ORDER BY observation_time DESC
            LIMIT 20;
        """, (icao,))
        
        rows = cur.fetchall()
        conn.close()

        results = [{
            "observation_time": row[0].isoformat(),
            "temperature_c": row[1],
            "dewpoint_c": row[2],
            "wind_dir_degrees": row[3],
            "wind_speed_kt": row[4],
            "visibility_statute_mi": row[5],
            "elevation": row[6],
            "cloud_cover": row[7],
            "cloud_base": row[8]
        } for row in rows]
            
        return jsonify(results)

    except Exception as e:
        print("Error querying DB:", e)
        return jsonify([]), 500
    
       
@app.route("/historic-rawMETAR")
def raw_metar_history():
    icao_raw = request.args.get('icao')
    startDate = request.args.get('startDateInput')
    endDate = request.args.get('endDateInput')
    
    if not icao_raw:
        return jsonify({"error": "Missing ICAO code"}), 400
    icao = icao_raw.upper()

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        cur.execute("""
            SELECT observation_time, raw_text
            FROM metar_reports
            WHERE station_id = %s
                    AND DATE(observation_time) BETWEEN %s AND %s
            ORDER BY observation_time DESC
            LIMIT 100;
        """, (icao, startDate, endDate))

        rows = cur.fetchall()        
        conn.close()

        historic_rawMETAR_results = [{
            "observation_time": row[0].isoformat(),
            "raw_text": row[1]
        } for row in rows]
    
        # historic_rawMETAR_results = [row[0] for row in rows]
            
        return jsonify(historic_rawMETAR_results)

    except Exception as e:
        print("Error querying DB:", e)
        return jsonify([]), 500


if __name__ == '__main__':
    app.run(debug=True)