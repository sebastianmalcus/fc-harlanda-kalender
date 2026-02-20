import requests
import json
from bs4 import BeautifulSoup
from icalendar import Calendar, Event
from datetime import datetime, timedelta

# --- INSTÄLLNINGAR ---
TEAM_NAME = "FC Härlanda"
# Spelprogrammet för Division 7B Göteborg (2025 som test)
SERIES_URL = "https://www.svenskfotboll.se/serier-cuper/spelprogram/division-7b-herr/123543/?scr=fixture"
MANUAL_EVENTS_FILE = "manual_events.json"

def generate():
    cal = Calendar()
    cal.add('prodid', '-//FC Härlanda//NONSGML v1.0//EN')
    cal.add('version', '2.0')
    cal.add('X-WR-CALNAME', '⚽️ FC Härlanda')
    cal.add('X-WR-TIMEZONE', 'Europe/Stockholm')
    cal.add('REFRESH-INTERVAL;VALUE=DURATION', 'PT12H')

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    # 1. HÄMTA MATCHER FRÅN SVENSK FOTBOLL
    try:
        print(f"Hämtar matcher från: {SERIES_URL}")
        res = requests.get(SERIES_URL, headers=headers, timeout=15)
        soup = BeautifulSoup(res.content, 'html.parser')
        rows = soup.find_all('tr')
        
        for row in rows:
            row_text = row.get_text()
            if TEAM_NAME.lower() in row_text.lower():
                cells = row.find_all('td')
                if len(cells) >= 6:
                    # Datum (YYYY-MM-DD)
                    date_str = "".join(filter(lambda x: x.isdigit() or x == '-', cells[0].text.strip()))
                    # Tid (HH:MM)
                    time_str = cells[1].text.strip()
                    if ":" not in time_str: time_str = "00:00"
                    
                    # Matchnamn och Arena
                    match_title = cells[2].text.strip().replace('\n', ' ').replace('  ', ' ')
                    arena = cells[5].text.strip()

                    try:
                        start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                        
                        e = Event()
                        e.add('summary', f"⚽️ Match: {match_title}")
                        e.add('dtstart', start_dt)
                        e.add('dtend', start_dt + timedelta(hours=2))
                        e.add('location', arena)
                        e.add('description', f"Hämtad från Svensk Fotboll\nArena: {arena}")
                        cal.add_component(e)
                        print(f"Match tillagd: {match_title}")
                    except Exception as e:
                        continue
    except Exception as e:
        print(f"Fel vid skrapning: {e}")

    # 2. LÄGG TILL MANUELLA HÄNDELSER (Träningar/Fester)
    try:
        with open(MANUAL_EVENTS_FILE, 'r', encoding='utf-8') as f:
            manual_data = json.load(f)
            for item in manual_data:
                start_dt = datetime.strptime(item['start'], "%Y-%m-%d %H:%M")
                
                e = Event()
                # Välj emoji baserat på text
                icon = "🏃‍♂️" if "träning" in item['summary'].lower() else "🎉" if "fest" in item['summary'].lower() else "📅"
                
                e.add('summary', f"{icon} {item['summary']}")
                e.add('dtstart', start_dt)
                e.add('dtend', start_dt + timedelta(hours=1.5))
                e.add('location', item.get('location', ''))
                e.add('description', item.get('description', ''))
                cal.add_component(e)
                print(f"Manuell händelse tillagd: {item['summary']}")
    except Exception as e:
        print(f"Inga manuella händelser hittades eller fel i JSON: {e}")

    # Spara filen
    with open("kalender.ics", "wb") as f:
        f.write(cal.to_ical())
    print("Filen kalender.ics har skapats framgångsrikt.")

if __name__ == "__main__":
    generate()
