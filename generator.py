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
    
    # Datumintervall för API-anropet (Från 1 jan 2025 -> 10 år framåt)
    date_from = "2025-01-01"
    date_to = (datetime.now() + timedelta(days=3650)).strftime('%Y-%m-%d')
    
    cal = Calendar()
    cal.add('prodid', '-//FC Harlanda//Fotbollskalender//SV')
    cal.add('version', '2.0')
    cal.add('x-wr-calname', 'FC Härlanda Prisoners')
    
    local_tz = pytz.timezone("Europe/Stockholm")

    # --- DEL 1: HÄMTA TRÄNINGAR FRÅN GOOGLE SHEETS ---
    try:
        response = requests.get(SHEET_CSV_URL)
        response.encoding = 'utf-8'
        reader = csv.DictReader(io.StringIO(response.text))
        for row in reader:
            try:
                # Kolumner: Datum, Start, Slut, Plats, Typ, Beskrivning
                start_dt = local_tz.localize(datetime.strptime(f"{row['Datum']} {row['Start']}", "%Y-%m-%d %H:%M"))
                end_dt = local_tz.localize(datetime.strptime(f"{row['Datum']} {row['Slut']}", "%Y-%m-%d %H:%M"))
                
                event = Event()
                event.add('summary', f"{row['Typ']}: {row['Plats']}")
                event.add('dtstart', start_dt)
                event.add('dtend', end_dt)
                event.add('location', row['Plats'])
                if row.get('Beskrivning'):
                    event.add('description', row['Beskrivning'])
                cal.add_component(event)
            except: continue
    except Exception as e:
        print(f"Sheet-fel: {e}")

    # --- DEL 2: HÄMTA MATCHER FRÅN FOGIS API (Med 10-års intervall) ---
    if FOGIS_API_KEY:
        try:
            api_url = f"https://forening-api.svenskfotboll.se/club/upcoming-games?from={date_from}&to={date_to}"
            headers = {'Ocp-Apim-Subscription-Key': FOGIS_API_KEY}
            
            res = requests.get(api_url, headers=headers)
            if res.status_code == 200:
                data = res.json()
                games = data.get('games', [])
                
                for g in games:
                    # Filtrera på ert TeamID: 107561
                    if g.get('homeTeamId') == 107561 or g.get('awayTeamId') == 107561:
                        home = g.get('homeTeamName', 'Hemmalag')
                        away = g.get('awayTeamName', 'Bortalag')
                        
                        event = Event()
                        event.add('summary', f"Match: {home} - {away}")
                        
                        raw_date = g.get('timeAsDateTime')
                        if raw_date:
                            # FOGIS skickar ibland med Z, ibland inte. Vi rensar för säkerhets skull.
                            clean_date = raw_date.split('.')[0].replace('Z', '').replace('T', ' ')
                            dt_start = datetime.strptime(clean_date, '%Y-%m-%d %H:%M:%S')
                            dt_start = local_tz.localize(dt_start)
                            
                            event.add('dtstart', dt_start)
                            event.add('dtend', dt_start + timedelta(hours=2))
                            event.add('location', g.get('venueName', 'Ej fastställt'))
                            event.add('description', f"Serie: {g.get('competitionName')}\nMatchnr: {g.get('gameNumber')}")
                            
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
