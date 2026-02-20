from flask import Flask, Response
import requests
import json
from bs4 import BeautifulSoup
from icalendar import Calendar, Event
from datetime import datetime, timedelta

app = Flask(__name__)

# INSTÄLLNINGAR
TEAM_NAME = "FC Härlanda"
# Notera "?scr=fixture" för att hamna direkt på spelprogrammet
SERIES_URL = "https://www.svenskfotboll.se/serier-cuper/spelprogram/division-7b-herr/123543/?scr=fixture"
# URL till din egen råa JSON-fil på GitHub (byt ut 'DITT_ANVÄNDARNAMN' och 'REPOT_NAMN')
# Du hittar denna genom att klicka på 'Raw' på filen i GitHub.
MANUAL_JSON_URL = "https://raw.githubusercontent.com/DITT_GITHUB_NAMN/DITT_REPO_NAMN/main/manual_events.json"

@app.route('/')
def home():
    return f"Kalendern för {TEAM_NAME} är live! Använd /kalender.ics i din kalender-app."

@app.route('/kalender.ics')
def generate_ical():
    cal = Calendar()
    cal.add('prodid', '-//FC Härlanda//')
    cal.add('version', '2.0')
    cal.add('X-WR-CALNAME', f'{TEAM_NAME} Spelschema')
    cal.add('X-WR-TIMEZONE', 'Europe/Stockholm')

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    # --- DEL 1: HÄMTA MATCHER FRÅN SVENSK FOTBOLL ---
    try:
        res = requests.get(SERIES_URL, headers=headers)
        soup = BeautifulSoup(res.content, 'html.parser')
        rows = soup.find_all('tr')
        
        for row in rows:
            if TEAM_NAME.lower() in row.text.lower():
                cells = row.find_all('td')
                if len(cells) >= 4:
                    # Vi letar efter datum (YYYY-MM-DD) och tid (HH:MM) i cellerna
                    date_str = ""
                    time_str = "00:00"
                    for c in cells:
                        val = c.text.strip()
                        if len(val) == 10 and "-" in val: date_str = val
                        if len(val) == 5 and ":" in val: time_str = val
                    
                    if date_str:
                        match_text = cells[2].text.strip().replace('\n', ' ')
                        arena = cells[5].text.strip() if len(cells) > 5 else "Ej angivet"
                        
                        start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                        
                        e = Event()
                        e.add('summary', match_text)
                        e.add('dtstart', start_dt)
                        e.add('dtend', start_dt + timedelta(hours=2))
                        e.add('location', arena)
                        cal.add_component(e)
    except Exception as err:
        print(f"Match-error: {err}")

    # --- DEL 2: HÄMTA MANUELLA HÄNDELSER FRÅN GITHUB ---
    try:
        # Vi hämtar JSON direkt från din GitHub-fil
        raw_res = requests.get(MANUAL_JSON_URL)
        if raw_res.status_code == 200:
            manual_data = raw_res.json()
            for item in manual_data:
                start_dt = datetime.strptime(item['start'], "%Y-%m-%d %H:%M")
                
                e = Event()
                e.add('summary', item['summary'])
                e.add('dtstart', start_dt)
                e.add('dtend', start_dt + timedelta(hours=2))
                e.add('location', item.get('location', ''))
                e.add('description', item.get('description', ''))
                cal.add_component(e)
    except Exception as err:
        print(f"Manual-error: {err}")

    return Response(cal.to_ical(), mimetype='text/calendar', headers={"Content-Disposition":"attachment;filename=kalender.ics"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
