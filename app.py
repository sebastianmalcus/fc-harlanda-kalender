import os
import json
import requests
import gspread
from google.oauth2.service_account import Credentials
from icalendar import Calendar, Event
from datetime import datetime, timedelta
import pytz

# --- KONFIGURATION ---
FOGIS_API_KEY = os.getenv('FOGIS_API_KEY', '').strip()
GOOGLE_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON', '').strip() # Se till att din GitHub Secret heter detta
SPREADSHEET_NAME = "FC Härlanda Kalender" # Ändra till exakt vad ditt kalkylark heter
TEAM_ID = 107561

def sync_and_generate():
    local_tz = pytz.timezone("Europe/Stockholm")
    
    # ==========================================
    # 1. ANSLUT TILL GOOGLE SHEETS
    # ==========================================
    print("Ansluter till Google Sheets...")
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = json.loads(GOOGLE_JSON)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    
    sheet = client.open(SPREADSHEET_NAME).sheet1
    all_rows = sheet.get_all_records()
    
    # Skapa ett register över alla MATCHER i arket (Radnummer börjar på 2 i gspread)
    # Key = Matchnr (sträng), Value = Dictionary med info om raden
    sheet_matches = {}
    for i, row in enumerate(all_rows):
        if row.get('Typ') == 'Match' and row.get('Matchnr'):
            sheet_matches[str(row['Matchnr'])] = {
                'row_index': i + 2,
                'datum': str(row.get('Datum', '')),
                'start': str(row.get('Start', '')),
                'plats': str(row.get('Plats', ''))
            }

    # ==========================================
    # 2. HÄMTA DATA FRÅN FOGIS
    # ==========================================
    print("Hämtar matcher från FOGIS...")
    date_from = "2026-01-01"
    date_to = "2026-12-31"
    url = f"https://forening-api.svenskfotboll.se/club/upcoming-games?from={date_from}&to={date_to}&w=3"
    
    headers = {
        'Ocp-Apim-Subscription-Key': FOGIS_API_KEY,
        'Accept': 'application/json'
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Fel från FOGIS: {response.status_code} - {response.text}")
        return

    fogis_data = response.json().get('games', [])
    prisoners_games = [g for g in fogis_data if g.get('homeTeamId') == TEAM_ID or g.get('awayTeamId') == TEAM_ID]
    
    api_match_numbers = [] # För att hålla koll på vilka matcher som fortfarande är aktiva
    
    # ==========================================
    # 3. SYNKRONISERA FOGIS -> GOOGLE SHEETS
    # ==========================================
    print("Synkroniserar data till kalkylarket...")
    
    for g in prisoners_games:
        match_nr = str(g.get('gameNumber'))
        api_match_numbers.append(match_nr)
        
        datum = g.get('timeAsDateTime', '').split('T')[0]
        tid = g.get('timeAsDateTime', '').split('T')[1][:5] if 'T' in g.get('timeAsDateTime', '') else ''
        plats = g.get('venueName', 'Ej fastställt')
        
        hemma = g.get('homeTeamName', '')
        borta = g.get('awayTeamName', '')
        resultat = g.get('result', '')
        beskrivning = f"Match: {hemma} - {borta}\nSerie: {g.get('competitionName')}"
        if resultat:
            beskrivning += f"\nResultat: {resultat}"

        row_data = [datum, tid, "", plats, "Match", beskrivning, match_nr]

        if match_nr in sheet_matches:
            # Matchen finns i arket. Har något ändrats?
            old_data = sheet_matches[match_nr]
            if old_data['datum'] != datum or old_data['start'] != tid or old_data['plats'] != plats:
                print(f"Uppdaterar match {match_nr}...")
                sheet.update(f"A{old_data['row_index']}:G{old_data['row_index']}", [row_data])
        else:
            # Matchen finns inte i arket, lägg till den!
            print(f"Lägger till ny match {match_nr}...")
            sheet.append_row(row_data)

    # 3b. Hitta matcher i arket som tagits bort från FOGIS
    for match_nr, data in sheet_matches.items():
        if match_nr not in api_match_numbers:
            print(f"Match {match_nr} saknas i FOGIS. Markerar som INSTÄLLD.")
            row_idx = data['row_index']
            # Skriv in "INSTÄLLD" i Beskrivnings-fältet (kolumn F)
            sheet.update_cell(row_idx, 6, "INSTÄLLD / BORTTAGEN FRÅN FOGIS")

    # ==========================================
    # 4. SKAPA KALENDER.ICS FRÅN KALKYLARKET
    # ==========================================
    print("Genererar kalenderfil...")
    # Läs hela arket på nytt för att få med uppdateringar och manuella träningar
    final_rows = sheet.get_all_records()
    
    cal = Calendar()
    cal.add('prodid', '-//FC Harlanda//Fotbollskalender//SV')
    cal.add('version', '2.0')
    cal.add('x-wr-calname', 'FC Härlanda Prisoners')
    
    for row in final_rows:
        try:
            datum_str = str(row.get('Datum', '')).strip()
            start_str = str(row.get('Start', '')).strip()
            
            if not datum_str or not start_str:
                continue
                
            start_dt = local_tz.localize(datetime.strptime(f"{datum_str} {start_str}", "%Y-%m-%d %H:%M"))
            
            slut_str = str(row.get('Slut', '')).strip()
            if slut_str:
                end_dt = local_tz.localize(datetime.strptime(f"{datum_str} {slut_str}", "%Y-%m-%d %H:%M"))
            else:
                end_dt = start_dt + timedelta(hours=2)

            beskrivning = str(row.get('Beskrivning', ''))
            
            # Hoppa över rader vi markerat som inställda
            if "INSTÄLLD" in beskrivning:
                continue

            event = Event()
            typ = str(row.get('Typ', 'Träning'))
            plats = str(row.get('Plats', ''))
            
            event.add('summary', f"{typ}: {plats}")
            event.add('dtstart', start_dt)
            event.add('dtend', end_dt)
            event.add('location', plats)
            event.add('description', beskrivning)
            
            cal.add_component(event)
        except Exception as e:
            print(f"Fel vid inläsning av rad: {e}")
            continue

    with open('kalender.ics', 'wb') as f:
        f.write(cal.to_ical())
    
    print("Allt klart! kalender.ics har sparats.")

if __name__ == "__main__":
    sync_and_generate()
