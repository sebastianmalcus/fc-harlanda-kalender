import os
import requests
import csv
from icalendar import Calendar, Event
from datetime import datetime, timedelta
import pytz
import io

def generate_calendar():
    # Inställningar
    SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQVrJh6-cKAJ86xyrZHNhjIaaCbffnM2jiEe9jYbU0C1JGysENbvXTKbiYTuL8wR9691tcTR2Oe8P4H/pub?output=csv"
    FOGIS_API_KEY = os.getenv('FOGIS_API_KEY')
    
    # ID-nummer hämtade från din JSON-data
    TEAM_ID = "107561" 
    
    cal = Calendar()
    cal.add('prodid', '-//FC Harlanda//Fotbollskalender//SV')
    cal.add('version', '2.0')
    cal.add('x-wr-calname', 'FC Härlanda Prisoners')
    
    local_tz = pytz.timezone("Europe/Stockholm")

    # --- DEL 1: HÄMTA TRÄNINGAR FRÅN GOOGLE SHEETS ---
    try:
        response = requests.get(SHEET_CSV_URL)
        response.encoding = 'utf-8'
        f = io.StringIO(response.text)
        reader = csv.DictReader(f)
        
        for row in reader:
            try:
                datum = row['Datum'].strip()
                start_tid = row['Start'].strip()
                slut_tid = row['Slut'].strip()
                plats = row['Plats'].strip()
                typ = row['Typ'].strip()
                beskrivning = row.get('Beskrivning', '').strip()
                
                event = Event()
                event.add('summary', f"{typ}: {plats}")
                
                start_dt = local_tz.localize(datetime.strptime(f"{datum} {start_tid}", "%Y-%m-%d %H:%M"))
                end_dt = local_tz.localize(datetime.strptime(f"{datum} {slut_tid}", "%Y-%m-%d %H:%M"))
                
                event.add('dtstart', start_dt)
                event.add('dtend', end_dt)
                event.add('location', plats)
                if beskrivning:
                    event.add('description', beskrivning)
                
                cal.add_component(event)
            except Exception as e:
                continue
                
    except Exception as e:
        print(f"Sheet-fel: {e}")

    # --- DEL 2: HÄMTA MATCHER FRÅN FOGIS API ---
    if FOGIS_API_KEY:
        try:
            # Vi använder Teams/Matcher med ditt specifika teamId
            api_url = f"https://api-fogis-association.azure-api.net/fogis/Teams/Matcher?teamId={TEAM_ID}"
            headers = {'Ocp-Apim-Subscription-Key': FOGIS_API_KEY}
            
            res = requests.get(api_url, headers=headers)
            if res.status_code == 200:
                matches = res.json()
                for m in matches:
                    home = m.get('homeTeamName', 'Hemmalag')
                    away = m.get('awayTeamName', 'Bortalag')
                    
                    event = Event()
                    event.add('summary', f"Match: {home} - {away}")
                    
                    # Tidshantering
                    raw_date = m.get('matchDate')
                    if raw_date:
                        # Konvertera ISO-tid (t.ex. 2025-04-15T19:00:00) till datetime
                        # Vi antar att tiden från API:et redan är lokal svensk tid
                        dt_start = datetime.fromisoformat(raw_date.replace('Z', ''))
                        dt_start = local_tz.localize(dt_start)
                        
                        event.add('dtstart', dt_start)
                        event.add('dtend', dt_start + timedelta(hours=2))
                        event.add('location', m.get('venueName', 'Ej fastställt'))
                        event.add('description', f"Serie: {m.get('competitionName')}\nMatchnr: {m.get('matchNumber')}")
                        
                        cal.add_component(event)
            else:
                print(f"API Error {res.status_code}")
        except Exception as e:
            print(f"API-fel: {e}")

    # Skriver ner den färdiga .ics-filen
    with open('kalender.ics', 'wb') as f:
        f.write(cal.to_ical())

if __name__ == "__main__":
    generate_calendar()
