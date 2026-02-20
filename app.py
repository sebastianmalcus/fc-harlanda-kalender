from flask import Flask, Response
import requests
import json
from bs4 import BeautifulSoup
from icalendar import Calendar, Event
from datetime import datetime, timedelta

app = Flask(__name__)

# --- INSTÄLLNINGAR ---
TEAM_NAME = "FC Härlanda"
# Länk till spelprogrammet för 2025 (Division 7B Göteborg)
SERIES_URL = "https://www.svenskfotboll.se/serier-cuper/spelprogram/division-7b-herr/123543/?scr=fixture"
# Vi läser lokalt från samma repo på Render
MANUAL_EVENTS_FILE = "manual_events.json"

@app.route('/')
def home():
    return f"<h1>Kalender-appen är online!</h1><p>Prenumerera på: <b>/kalender.ics</b></p>"

@app.route('/kalender.ics')
def generate_ical():
    cal = Calendar()
    cal.add('prodid', '-//FC Härlanda//NONSGML v1.0//EN')
    cal.add('version', '2.0')
    cal.add('X-WR-CALNAME', 'FC Härlanda Spelschema')
    cal.add('X-WR-TIMEZONE', 'Europe/Stockholm')
    cal.add('REFRESH-INTERVAL;VALUE=DURATION', 'PT12H') # Ber kalender-appar hämta på nytt var 12:e timme

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    # 1. HÄMTA MATCHER FRÅN SVENSK FOTBOLL
    try:
        res = requests.get(SERIES_URL, headers=headers, timeout=10)
        soup = BeautifulSoup(res.content, 'html.parser')
        
        # Vi letar efter rader i tabellen på sidan
        rows = soup.select('tr')
        for row in rows:
            row_text = row.get_text()
            if TEAM_NAME.lower() in row_text.lower():
                cells = row.find_all('td')
                if len(cells) >= 4:
                    # Extrahera datum (YYYY-MM-DD)
                    date_cell = row.find('span', class_='date') or cells[0]
                    date_str = "".join(filter(lambda x: x.isdigit() or x == '-', date_cell.text.strip()))
                    
                    # Extrahera tid (HH:MM)
                    time_str = cells[1].text.strip() if len(cells) > 1 else "00:00"
                    if ":" not in time_str: time_str = "00:00"

                    # Extrahera matchnamn (Lag A - Lag B)
                    match_name = cells[2].text.strip().replace('\n', ' ').replace('  ', ' ')
                    
                    # Extrahera arena
                    arena = cells[5].text.strip() if len(cells) > 5 else "Ej angivet"

                    try:
                        start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                        
                        e = Event()
                        e.add('summary', match_name)
                        e.add('dtstart', start_dt)
                        e.add('dtend', start_dt + timedelta(hours=2))
                        e.add('location', arena)
                        e.add('description', f"Seriematch - Hämtad från Svensk Fotboll\nArena: {arena}")
                        cal.add_component(e)
                    except Exception as parse_err:
                        print(f"Kunde inte tolka datum: {date_str} {time_str}")
    except Exception as e:
        print(f"Fel vid skrapning: {e}")

    # 2. LÄGG TILL MANUELLA HÄNDELSER FRÅN DIN JSON-FIL
    try:
        with open(MANUAL_EVENTS_FILE, 'r', encoding='utf-8') as f:
            manual_data = json.load(f)
            for item in manual_data:
                start_dt = datetime.strptime(item['start'], "%Y-%m-%d %H:%M")
                
                e = Event()
                e.add('summary', item['summary'])
                e.add('dtstart', start_dt)
                e.add('dtend', start_dt + timedelta(hours=2))
                e.add('location', item.get('location', ''))
                e.add('description', item.get('description', ''))
                cal.add_component(e)
    except Exception as e:
        print(f"Fel vid inläsning av manuella events: {e}")

    return Response(
        cal.to_ical(),
        mimetype='text/calendar',
        headers={"Content-Disposition": "attachment; filename=kalender.ics"}
    )

if __name__ == "__main__":
    # För lokal testning, men Render använder Gunicorn
    app.run(host='0.0.0.0', port=5000)
