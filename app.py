from flask import Flask, Response
import requests
import json
from bs4 import BeautifulSoup
from icalendar import Calendar, Event
from datetime import datetime, timedelta

app = Flask(__name__)

# Inställningar - VIKTIGT: Namnet måste matcha exakt i tabellen
TEAM_NAME = "FC Härlanda" 
SERIES_URL = "https://www.svenskfotboll.se/serier-cuper/tabell-och-resultat/division-7b-herr/123543/"

@app.route('/')
def home():
    return "Kalendern är aktiv! Prenumerera via /kalender.ics"

@app.route('/kalender.ics')
def generate_ical():
    cal = Calendar()
    cal.add('prodid', '-//FC Härlanda//')
    cal.add('version', '2.0')
    cal.add('X-WR-CALNAME', 'FC Härlanda')

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        res = requests.get(SERIES_URL, headers=headers)
        soup = BeautifulSoup(res.content, 'html.parser')
        
        # Vi letar efter rader i spelprogram-tabellen
        rows = soup.find_all('tr')
        print(f"Hittade {len(rows)} rader i tabellen") # Syns i Renders loggar

        for row in rows:
            cells = row.find_all('td')
            row_text = row.get_text()
            
            if TEAM_NAME.lower() in row_text.lower() and len(cells) >= 4:
                try:
                    # Ofta: Datum(0), Tid(1), Match(2), Arena(5)
                    # Men vi letar efter datumformatet YYYY-MM-DD
                    date_val = ""
                    time_val = "00:00"
                    
                    for cell in cells:
                        val = cell.text.strip()
                        if len(val) == 10 and val.count('-') == 2: # Hittat datumet
                            date_val = val
                        if len(val) == 5 and ":" in val: # Hittat tiden
                            time_val = val
                    
                    if date_val:
                        match_name = cells[2].text.strip().replace('\n', ' ')
                        arena = cells[5].text.strip() if len(cells) > 5 else "Ej angivet"
                        
                        full_date = datetime.strptime(f"{date_val} {time_val}", "%Y-%m-%d %H:%M")
                        
                        event = Event()
                        event.add('summary', match_name)
                        event.add('dtstart', full_date)
                        event.add('dtend', full_date + timedelta(hours=2))
                        event.add('location', arena)
                        cal.add_component(event)
                        print(f"Match tillagd: {match_name}")
                except Exception as e:
                    print(f"Fel vid rad-analys: {e}")
                    continue

    except Exception as e:
        print(f"Server-fel: {e}")

    return Response(cal.to_ical(), mimetype='text/calendar')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
