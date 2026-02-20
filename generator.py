import requests
import json
from bs4 import BeautifulSoup
from icalendar import Calendar, Event
from datetime import datetime, timedelta

TEAM_NAME = "FC Härlanda"
SERIES_URL = "https://www.svenskfotboll.se/serier-cuper/spelprogram/division-7b-herr/123543/?scr=fixture"
MANUAL_EVENTS_FILE = "manual_events.json"

def generate():
    cal = Calendar()
    cal.add('prodid', '-//FC Härlanda//')
    cal.add('version', '2.0')
    cal.add('X-WR-CALNAME', 'FC Härlanda')

    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # 1. Hämta matcher
    try:
        res = requests.get(SERIES_URL, headers=headers)
        soup = BeautifulSoup(res.content, 'html.parser')
        for row in soup.find_all('tr'):
            if TEAM_NAME.lower() in row.text.lower():
                cells = row.find_all('td')
                if len(cells) >= 6:
                    date_str = "".join(filter(lambda x: x.isdigit() or x == '-', cells[0].text.strip()))
                    time_str = cells[1].text.strip()
                    if ":" not in time_str: time_str = "00:00"
                    
                    start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                    e = Event()
                    e.add('summary', cells[2].text.strip())
                    e.add('dtstart', start_dt)
                    e.add('dtend', start_dt + timedelta(hours=2))
                    e.add('location', cells[5].text.strip())
                    cal.add_component(e)
    except Exception as e: print(f"Error scraping: {e}")

    # 2. Manuella händelser
    try:
        with open(MANUAL_EVENTS_FILE, 'r', encoding='utf-8') as f:
            for item in json.load(f):
                start_dt = datetime.strptime(item['start'], "%Y-%m-%d %H:%M")
                e = Event()
                e.add('summary', item['summary'])
                e.add('dtstart', start_dt)
                e.add('dtend', start_dt + timedelta(hours=2))
                cal.add_component(e)
    except: pass

    with open("kalender.ics", "wb") as f:
        f.write(cal.to_ical())

if __name__ == "__main__":
    generate()
