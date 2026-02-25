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
    # Klubb-ID för FC Härlanda Prisoners (detta kan behöva justeras om det inte ger träff)
    CLUB_ID = "123543" 
    
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

    # --- DEL 2: HÄMTA MATCHER FRÅN FOGIS API ---
    if FOGIS_API_KEY:
        try:
            # Vi anropar deras endpoint för klubbens matcher
            api_url = f"https://api-fogis-association.azure-api.net/fogis/Clubs/Matcher?clubId={CLUB_ID}"
            headers = {'Ocp-Apim-Subscription-Key': FOGIS_API_KEY}
            
            res = requests.get(api_url, headers=headers)
            if res.status_code == 200:
                matches = res.json()
                for m in matches:
                    # Skapa match-event
                    event = Event()
                    home = m.get('homeTeamName', 'Hemmalag')
                    away = m.get('awayTeamName', 'Bortalag')
                    event.add('summary', f"Match: {home} - {away}")
                    
                    # Tidshantering från ISO-format
                    match_date = datetime.fromisoformat(m.get('matchDate').replace('Z', '+00:00'))
                    event.add('dtstart', match_date)
                    event.add('dtend', match_date + timedelta(hours=2))
                    event.add('location', m.get('venueName', 'Ej fastställt'))
                    event.add('description', f"Serie: {m.get('tournamentName')}\nMatchnr: {m.get('matchNumber')}")
                    cal.add_component(event)
        except Exception as e:
            print(f"API-fel: {e}")

    with open('kalender.ics', 'wb') as f:
        f.write(cal.to_ical())

if __name__ == "__main__":
    generate_calendar()
