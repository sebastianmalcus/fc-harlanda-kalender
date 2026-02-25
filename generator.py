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
    FOGIS_API_KEY = os.getenv('FOGIS_API_KEY')
    
    # Intervall: 1 jan 2025 -> 10 år framåt
    date_from = "2025-01-01"
    date_to = (datetime.now() + timedelta(days=3650)).strftime('%Y-%m-%d')
    
    cal = Calendar()
    cal.add('prodid', '-//FC Harlanda//Fotbollskalender//SV')
    cal.add('version', '2.0')
    cal.add('x-wr-calname', 'FC Härlanda Prisoners')
    local_tz = pytz.timezone("Europe/Stockholm")

    # --- DEL 1: GOOGLE SHEETS ---
    print("--- STARTAR INLÄSNING FRÅN GOOGLE SHEETS ---")
    try:
        response = requests.get(SHEET_CSV_URL)
        reader = csv.DictReader(io.StringIO(response.text))
        for row in reader:
            try:
                start_dt = local_tz.localize(datetime.strptime(f"{row['Datum']} {row['Start']}", "%Y-%m-%d %H:%M"))
                event = Event()
                event.add('summary', f"{row['Typ']}: {row['Plats']}")
                event.add('dtstart', start_dt)
                event.add('dtend', start_dt + timedelta(hours=2))
                cal.add_component(event)
            except: continue
        print("Sheets klart.")
    except: print("Sheets misslyckades.")

    # --- DEL 2: FOGIS API ---
    print("\n--- STARTAR ANROP TILL FOGIS API ---")
    if FOGIS_API_KEY:
        try:
            api_url = f"https://forening-api.svenskfotboll.se/club/upcoming-games?from={date_from}&to={date_to}"
            
            # Vi skickar med BÅDA varianterna av headers för att vara helt säkra
            headers = {
                'Ocp-Apim-Subscription-Key': FOGIS_API_KEY.strip(),
                'x-api-key': FOGIS_API_KEY.strip(),
                'Cache-Control': 'no-cache'
            }
            
            print(f"Anropar med maskad nyckel: {FOGIS_API_KEY[:4]}...")
            res = requests.get(api_url, headers=headers)
            print(f"HTTP Status: {res.status_code}")
            
            if res.status_code == 200:
                data = res.json()
                games = data.get('games', [])
                print(f"Hittade {len(games)} matcher i API-svaret.")
                
                for g in games:
                    # Filtrera på Team ID 107561
                    if g.get('homeTeamId') == 107561 or g.get('awayTeamId') == 107561:
                        event = Event()
                        event.add('summary', f"Match: {g.get('homeTeamName')} - {g.get('awayTeamName')}")
                        raw_date = g.get('timeAsDateTime')
                        if raw_date:
                            clean_date = raw_date.split('.')[0].replace('Z', '').replace('T', ' ')
                            dt_start = local_tz.localize(datetime.strptime(clean_date, '%Y-%m-%d %H:%M:%S'))
                            event.add('dtstart', dt_start)
                            event.add('dtend', dt_start + timedelta(hours=2))
                            event.add('location', g.get('venueName', 'Ej fastställt'))
                            cal.add_component(event)
                print("Matcher inlagda.")
            else:
                print(f"API Error: {res.text}")
        except Exception as e:
            print(f"API Systemfel: {e}")

    with open('kalender.ics', 'wb') as f:
        f.write(cal.to_ical())
    print("\n--- KLART ---")

if __name__ == "__main__":
    generate_calendar()
