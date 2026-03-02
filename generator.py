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
GOOGLE_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON', '').strip() 
SPREADSHEET_NAME = "kalenderFCHP"
TEAM_ID = 107561

def sync_and_generate():
    local_tz = pytz.timezone("Europe/Stockholm")
    print("🚀 Startar synkronisering...")

    # 1. ANSLUT TILL GOOGLE SHEETS (Vi vet att detta fungerar!)
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GOOGLE_JSON)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME).sheet1
    
    # 2. HÄMTA MATCHER FRÅN FOGIS
    # Vi använder en Session för att garantera att headers skickas korrekt
    session = requests.Session()
    session.headers.update({
        'Ocp-Apim-Subscription-Key': FOGIS_API_KEY,
        'Cache-Control': 'no-cache',
        'Accept': 'application/json'
    })
    
    date_from, date_to = "2026-01-01", "2026-12-31"
    # Vi testar att skicka nyckeln både i header OCH som parameter i URL:en
    url = f"https://forening-api.svenskfotboll.se/club/upcoming-games?from={date_from}&to={date_to}&w=3&subscription-key={FOGIS_API_KEY}"
    
    print(f"⏳ Anropar FOGIS...")
    response = session.get(url)
    
    if response.status_code != 200:
        print(f"❌ FOGIS vägrar fortfarande (Status {response.status_code})")
        print(f"Svar från server: {response.text}")
        return

    data = response.json()
    games = data.get('games', [])
    prisoners_games = [g for g in games if g.get('homeTeamId') == TEAM_ID or g.get('awayTeamId') == TEAM_ID]
    
    print(f"✅ Succé! Hittade {len(prisoners_games)} matcher för Prisoners.")

    # 3. UPPDATERA ARKET
    all_rows = sheet.get_all_records()
    # Skapa index (Matchnr -> Radnummer)
    sheet_matches = {str(r.get('Matchnr')): i + 2 for i, r in enumerate(all_rows) if r.get('Matchnr')}

    for g in prisoners_games:
        m_nr = str(g.get('gameNumber'))
        datum = g.get('timeAsDateTime', '').split('T')[0]
        tid = g.get('timeAsDateTime', '').split('T')[1][:5] if 'T' in g.get('timeAsDateTime', '') else ''
        plats = g.get('venueName', 'Ej fastställt')
        desc = f"Match: {g.get('homeTeamName')} - {g.get('awayTeamName')}\nSerie: {g.get('competitionName')}"
        
        row = [datum, tid, "", plats, "Match", desc, m_nr]

        if m_nr in sheet_matches:
            # Uppdatera befintlig
            sheet.update(f"A{sheet_matches[m_nr]}:G{sheet_matches[m_nr]}", [row])
        else:
            # Lägg till ny
            sheet.append_row(row)

    print("🎉 Kalkylarket är nu uppdaterat med riktiga matcher!")

if __name__ == "__main__":
    sync_and_generate()
