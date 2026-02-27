import os
import requests
import csv
from icalendar import Calendar, Event
from datetime import datetime, timedelta
import pytz
import io

def generate_calendar():
    # --- KONFIGURATION ---
    SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQVrJh6-cKAJ86xyrZHNhjIaaCbffnM2jiEe9jYbU0C1JGysENbvXTKbiYTuL8wR9691tcTR2Oe8P4H/pub?output=csv"
    FOGIS_API_KEY = os.getenv('FOGIS_API_KEY', '').strip()
    
    # Vi hämtar matcher för hela 2026
    date_from = datetime.now().strftime('%Y-%m-%d')
    date_to = "2026-12-31"
    
    cal = Calendar()
    cal.add('prodid', '-//FC Harlanda//Fotbollskalender//SV')
    cal.add('version', '2.0')
    cal.add('x-wr-calname', 'FC Härlanda Prisoners')
    local_tz = pytz.timezone("Europe/Stockholm")

    # --- DEL 1: GOOGLE SHEETS (TRÄNINGAR) ---
    try:
        response = requests.get(SHEET_CSV_URL)
        reader = csv.DictReader(io.StringIO(response.text))
        for row in reader:
            try:
                start_dt = local_tz.localize(datetime.strptime(f"{row['Datum']} {row['Start']}", "%Y-%m-%d %H:%M"))
                end_dt = local_tz.localize(datetime.strptime(f"{row['Datum']} {row['Slut']}", "%Y-%m-%d %H:%M"))
                event = Event()
                event.add('summary', f"{row['Typ']}: {row['Plats']}")
                event.add('dtstart', start_dt)
                event.add('dtend', end_dt)
                event.add('location', row['Plats'])
                cal.add_component(event)
            except: continue
    except: pass

    # --- DEL 2: FOGIS API (MATCHER 2026) ---
    if FOGIS_API_KEY:
        # Vi använder den beprövade URL:en med parametern w=3 för alla matcher
        api_url = f"https://forening-api.svenskfotboll.se/club/upcoming-games?from={date_from}&to={date_to}&w=3"
        headers = {'Ocp-Apim-Subscription-Key': FOGIS_API_KEY}
        
        try:
            res = requests.get(api_url, headers=headers)
            if res.status_code == 200:
                data = res.json()
                for g in data.get('games', []):
                    # Filtrera på Prisoners Team ID: 107561
                    if g.get('homeTeamId') == 107561 or g.get('awayTeamId') == 107561:
                        event = Event()
                        event.add('summary', f"Match: {g.get('homeTeamName')} - {g.get('awayTeamName')}")
                        
                        raw_date = g.get('timeAsDateTime')
                        if raw_date:
                            dt_start = local_tz.localize(datetime.fromisoformat(raw_date.replace('Z', '')))
                            event.add('dtstart', dt_start)
                            event.add('dtend', dt_start + timedelta(hours=2))
                            event.add('location', g.get('venueName', 'Ej fastställt'))
                            event.add('description', f"Serie: {g.get('competitionName')}\nMatchnr: {g.get('gameNumber')}")
                            cal.add_component(event)
        except: pass

    with open('kalender.ics', 'wb') as f:
        f.write(cal.to_ical())

if __name__ == "__main__":
    generate_calendar()
