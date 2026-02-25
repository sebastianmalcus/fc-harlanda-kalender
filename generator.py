import requests
import csv
from icalendar import Calendar, Event
from datetime import datetime, timedelta
import pytz
import io

def generate_calendar():
    # Din publicerade CSV-länk från Google Sheets
    SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQVrJh6-cKAJ86xyrZHNhjIaaCbffnM2jiEe9jYbU0C1JGysENbvXTKbiYTuL8wR9691tcTR2Oe8P4H/pub?output=csv"
    
    cal = Calendar()
    cal.add('prodid', '-//FC Harlanda//Fotbollskalender//SV')
    cal.add('version', '2.0')
    cal.add('x-wr-calname', 'FC Härlanda Total')
    
    local_tz = pytz.timezone("Europe/Stockholm")

    # --- DEL 1: HÄMTA FRÅN GOOGLE SHEETS (TRÄNINGAR/BOKNINGAR) ---
    try:
        response = requests.get(SHEET_CSV_URL)
        response.encoding = 'utf-8'
        # Vi använder StringIO för att läsa texten som en fil
        f = io.StringIO(response.text)
        reader = csv.DictReader(f)
        
        for row in reader:
            # Förväntade kolumner: Datum, Start, Slut, Plats, Typ
            try:
                datum = row['Datum'].strip()
                start_tid = row['Start'].strip()
                slut_tid = row['Slut'].strip()
                plats = row['Plats'].strip()
                typ = row['Typ'].strip()
                
                event = Event()
                event.add('summary', f"{typ}: {plats}")
                
                # Skapar datetime-objekt
                start_dt = local_tz.localize(datetime.strptime(f"{datum} {start_tid}", "%Y-%m-%d %H:%M"))
                end_dt = local_tz.localize(datetime.strptime(f"{datum} {slut_tid}", "%Y-%m-%d %H:%M"))
                
                event.add('dtstart', start_dt)
                event.add('dtend', end_dt)
                event.add('location', plats)
                event.add('description', f"Inlagt via Google Sheets")
                
                cal.add_component(event)
            except (KeyError, ValueError) as e:
                print(f"Hoppar över rad pga felaktigt format: {e}")
                continue
                
    except Exception as e:
        print(f"Kunde inte läsa Google Sheets: {e}")

    # --- DEL 2: HÄMTA MATCHER (VÄNTAR PÅ API-NYCKEL) ---
    # Temporär testmatch tills FOGIS-nyckeln är på plats
    test_event = Event()
    test_event.add('summary', 'VÄNTAR PÅ API: FC Härlanda Match')
    test_event.add('dtstart', local_tz.localize(datetime(2025, 4, 15, 19, 0)))
    test_event.add('dtend', local_tz.localize(datetime(2025, 4, 15, 21, 0)))
    cal.add_component(test_event)

    # Skriver ner den färdiga .ics-filen
    with open('kalender.ics', 'wb') as f:
        f.write(cal.to_ical())

if __name__ == "__main__":
    generate_calendar()
