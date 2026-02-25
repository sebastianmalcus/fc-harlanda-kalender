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
    
    # Datumintervall för anropet
    date_from = "2025-01-01"
    date_to = (datetime.now() + timedelta(days=3650)).strftime('%Y-%m-%d')
    
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
    except: print("Sheets misslyckades.")

    # --- DEL 2: FOGIS API (MATCHER) ---
    if FOGIS_API_KEY:
        # URL som vi nu vet fungerar med din nyckel
        api_url = f"https://forening-api.svenskfotboll.se/club/upcoming-games?from={date_from}&to={date_to}&w=3"
        headers = {'Ocp-Apim-Subscription-Key': FOGIS_API_KEY}
        
        try:
            res = requests.get(api_url, headers=headers)
            if res.status_code == 200:
                data = res.json()
                games = data.get('games', [])
                
                for g in games:
                    # Vi filtrerar på Team ID 107561 (Prisoners)
                    if g.get('homeTeamId') == 107561 or g.get('awayTeamId') == 107561:
                        home = g.get('homeTeamName')
                        away = g.get('awayTeamName')
                        
                        event = Event()
                        # Om matchen är spelad lägger vi till resultatet i rubriken
                        summary = f"Match: {home} - {away}"
                        if g.get('isFinished') and g.get('result'):
                            summary += f" ({g.get('result')})"
                        
                        event.add('summary', summary)
                        
                        # Tidshantering från timeAsDateTime (t.ex. 2026-04-07T20:15:00)
                        raw_date = g.get('timeAsDateTime')
                        if raw_date:
                            dt_start = datetime.fromisoformat(raw_date.replace('Z', ''))
                            dt_start = local_tz.localize(dt_start)
                            
                            event.add('dtstart', dt_start)
                            event.add('dtend', dt_start + timedelta(hours=2))
                            event.add('location', g.get('venueName', 'Ej fastställt'))
                            
                            # Lägg till domare och serie i beskrivningen
                            desc = f"Serie: {g.get('competitionName')}\n"
                            if g.get('referees') and g.get('referees').get('name'):
                                desc += f"Domare: {g['referees']['name']}"
                            event.add('description', desc)
                            
                            cal.add_component(event)
            else:
                print(f"API Error {res.status_code}")
        except Exception as e:
            print(f"API Systemfel: {e}")

    # --- SPARA FIL ---
    with open('kalender.ics', 'wb') as f:
        f.write(cal.to_ical())

if __name__ == "__main__":
    generate_calendar()
