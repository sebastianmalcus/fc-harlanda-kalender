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
    
    # Tidsintervall: 1 jan 2025 till 10 år framåt
    date_from = "2025-01-01"
    date_to = (datetime.now() + timedelta(days=3650)).strftime('%Y-%m-%d')
    
    cal = Calendar()
    cal.add('prodid', '-//FC Harlanda//Fotbollskalender//SV')
    cal.add('version', '2.0')
    cal.add('x-wr-calname', 'FC Härlanda Prisoners')
    
    local_tz = pytz.timezone("Europe/Stockholm")

    # --- DEL 1: GOOGLE SHEETS (TRÄNINGAR) ---
    print("--- STARTAR INLÄSNING FRÅN GOOGLE SHEETS ---")
    try:
        response = requests.get(SHEET_CSV_URL)
        response.encoding = 'utf-8'
        reader = csv.DictReader(io.StringIO(response.text))
        count_sheets = 0
        for row in reader:
            try:
                start_dt = local_tz.localize(datetime.strptime(f"{row['Datum']} {row['Start']}", "%Y-%m-%d %H:%M"))
                event = Event()
                event.add('summary', f"{row['Typ']}: {row['Plats']}")
                event.add('dtstart', start_dt)
                event.add('dtend', start_dt + timedelta(hours=2))
                cal.add_component(event)
                count_sheets += 1
            except: continue
        print(f"Hittade {count_sheets} händelser i Google Sheets.")
    except Exception as e:
        print(f"FEL vid inläsning av Sheets: {e}")

    # --- DEL 2: FOGIS API (MATCHER) ---
    print("\n--- STARTAR ANROP TILL FOGIS API ---")
    if not FOGIS_API_KEY:
        print("FEL: Ingen FOGIS_API_KEY hittades i GitHub Secrets!")
    else:
        try:
            api_url = f"https://forening-api.svenskfotboll.se/club/upcoming-games?from={date_from}&to={date_to}"
            headers = {'Ocp-Apim-Subscription-Key': FOGIS_API_KEY}
            
            print(f"Anropar: {api_url}")
            res = requests.get(api_url, headers=headers)
            
            print(f"HTTP Status: {res.status_code}")
            
            if res.status_code == 200:
                data = res.json()
                games = data.get('games', [])
                print(f"API:et returnerade {len(games)} matcher totalt för klubben.")
                
                match_count = 0
                for g in games:
                    h_id = g.get('homeTeamId')
                    a_id = g.get('awayTeamId')
                    h_name = g.get('homeTeamName')
                    a_name = g.get('awayTeamName')
                    
                    # LOGGA ALLA MATCHER SOM HITTAS
                    print(f"Kollar match: {h_name} ({h_id}) vs {a_name} ({a_id})")
                    
                    # Kolla mot ert Team ID (107561) eller om namnet innehåller "Prisoners"
                    if h_id == 107561 or a_id == 107561 or "Prisoners" in str(h_name) or "Prisoners" in str(a_name):
                        print(f"   >>> MATCH TRÄFF! Lägger till i kalendern.")
                        event = Event()
                        event.add('summary', f"Match: {h_name} - {a_name}")
                        
                        raw_date = g.get('timeAsDateTime')
                        if raw_date:
                            clean_date = raw_date.split('.')[0].replace('Z', '').replace('T', ' ')
                            dt_start = local_tz.localize(datetime.strptime(clean_date, '%Y-%m-%d %H:%M:%S'))
                            event.add('dtstart', dt_start)
                            event.add('dtend', dt_start + timedelta(hours=2))
                            event.add('location', g.get('venueName', 'Ej fastställt'))
                            cal.add_component(event)
                            match_count += 1
                
                print(f"Totalt antal matcher inlagda för Prisoners: {match_count}")
            else:
                print(f"API Error: {res.text}")
                
        except Exception as e:
            print(f"Systemfel vid API-anrop: {e}")

    # --- SPARA FIL ---
    with open('kalender.ics', 'wb') as f:
        f.write(cal.to_ical())
    print("\n--- FILEN 'kalender.ics' HAR SKAPATS ---")

if __name__ == "__main__":
    generate_calendar()
