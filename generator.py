import os
import requests
import csv
from icalendar import Calendar, Event
from datetime import datetime, timedelta
import pytz
import io

def generate_calendar():
    SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQVrJh6-cKAJ86xyrZHNhjIaaCbffnM2jiEe9jYbU0C1JGysENbvXTKbiYTuL8wR9691tcTR2Oe8P4H/pub?output=csv"
    FOGIS_API_KEY = os.getenv('FOGIS_API_KEY')
    
    date_from = "2025-01-01"
    date_to = (datetime.now() + timedelta(days=3650)).strftime('%Y-%m-%d')
    
    cal = Calendar()
    cal.add('prodid', '-//FC Harlanda//Fotbollskalender//SV')
    cal.add('version', '2.0')
    cal.add('x-wr-calname', 'FC Härlanda Prisoners')
    
    local_tz = pytz.timezone("Europe/Stockholm")

    # --- DEL 1: GOOGLE SHEETS ---
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
    except: print("Kunde inte läsa Sheets")

    # --- DEL 2: FOGIS API MED LOGGNING ---
    if FOGIS_API_KEY:
        try:
            api_url = f"https://forening-api.svenskfotboll.se/club/upcoming-games?from={date_from}&to={date_to}"
            headers = {'Ocp-Apim-Subscription-Key': FOGIS_API_KEY}
            
            print(f"Anropar API: {api_url}")
            res = requests.get(api_url, headers=headers)
            
            if res.status_code == 200:
                data = res.json()
                games = data.get('games', [])
                print(f"Antal matcher hittade totalt i API-svaret: {len(games)}")
                
                for g in games:
                    home_id = g.get('homeTeamId')
                    away_id = g.get('awayTeamId')
                    home_name = g.get('homeTeamName')
                    away_name = g.get('awayTeamName')
                    
                    # Logga varje match för att se ID och namn i GitHub Actions-loggen
                    print(f"Match hittad: {home_name} ({home_id}) vs {away_name} ({away_id})")
                    
                    # Kolla om Prisoners (107561) spelar
                    if home_id == 107561 or away_id == 107561:
                        print(f"-> MATCH MATCHAD! Lägger till {home_name} - {away_name}")
                        event = Event()
                        event.add('summary', f"Match: {home_name} - {away_name}")
                        
                        raw_date = g.get('timeAsDateTime')
                        if raw_date:
                            clean_date = raw_date.split('.')[0].replace('Z', '').replace('T', ' ')
                            dt_start = local_tz.localize(datetime.strptime(clean_date, '%Y-%m-%d %H:%M:%S'))
                            event.add('dtstart', dt_start)
                            event.add('dtend', dt_start + timedelta(hours=2))
                            event.add('location', g.get('venueName', 'Ej fastställt'))
                            cal.add_component(event)
            else:
                print(f"API Error {res.status_code}: {res.text}")
        except Exception as e:
            print(f"API-fel: {e}")

    with open('kalender.ics', 'wb') as f:
        f.write(cal.to_ical())

if __name__ == "__main__":
    generate_calendar()
