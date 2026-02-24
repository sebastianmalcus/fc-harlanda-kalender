import requests
from bs4 import BeautifulSoup
from icalendar import Calendar, Event
from datetime import datetime
import pytz

def generate_calendar():
    url = "https://www.svenskfotboll.se/serier-cuper/tabell-och-resultat/division-7b-herr/123543/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    cal = Calendar()
    cal.add('prodid', '-//FC Harlanda//Fotbollskalender//SV')
    cal.add('version', '2.0')
    cal.add('x-wr-calname', 'FC Härlanda - Div 7B')

    # Hittar alla rader i matchtabellen
    matches = soup.find_all('tr', class_='match-row')

    for match in matches:
        try:
            # Extrahera lag (SUMMARY)
            home_team = match.find('span', class_='home-team').text.strip()
            away_team = match.find('span', class_='away-team').text.strip()
            
            # Extrahera datum och tid
            # Svensk Fotboll använder ofta data-attribut för datum
            date_str = match.find('span', class_='date').text.strip() # t.ex. "2025-04-15"
            time_str = match.find('span', class_='time').text.strip() # t.ex. "19:00"
            
            # Skapa händelse
            event = Event()
            event.add('summary', f"{home_team} - {away_team}")
            
            # Kombinera datum och tid (Sverige använder CET/CEST)
            local = pytz.timezone("Europe/Stockholm")
            naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            local_dt = local.localize(naive_dt, is_dst=None)
            utc_dt = local_dt.astimezone(pytz.utc)

            event.add('dtstart', utc_dt)
            event.add('dtend', utc_dt) # Du kan lägga till +90 min här om du vill
            event.add('description', 'Division 7B Herr')
            
            cal.add_component(event)
        except:
            continue # Hoppa över rader som inte är kompletta matcher

    with open('kalender.ics', 'wb') as f:
        f.write(cal.to_ical())

if __name__ == "__main__":
    generate_calendar()
