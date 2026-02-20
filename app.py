from flask import Flask, Response
import requests
import json
from bs4 import BeautifulSoup
from icalendar import Calendar, Event
from datetime import datetime, timedelta

app = Flask(__name__)

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

    # Hämta från webben
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(SERIES_URL, headers=headers)
    soup = BeautifulSoup(res.content, 'html.parser')
    
    for row in soup.find_all('tr'):
        if TEAM_NAME in row.text:
            cols = row.find_all('td')
            if len(cols) >= 6:
                try:
                    date_str = cols[0].text.strip()
                    time_str = cols[1].text.strip()
                    match_name = cols[2].text.strip().replace('\n', ' ')
                    arena = cols[5].text.strip()
                    full_date = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                    
                    event = Event()
                    event.add('summary', match_name)
                    event.add('dtstart', full_date)
                    event.add('dtend', full_date + timedelta(hours=2))
                    event.add('location', arena)
                    cal.add_component(event)
                except: continue

    return Response(cal.to_ical(), mimetype='text/calendar')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
