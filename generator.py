import os
import json
import requests
import gspread
from google.oauth2.service_account import Credentials
from icalendar import Calendar, Event
from datetime import datetime, timedelta
import pytz

# --- KONFIGURATION ---
# Vi hämtar nyckeln och rensar eventuella osynliga tecken direkt
FOGIS_API_KEY = os.getenv('FOGIS_API_KEY', '').strip()
GOOGLE_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON', '').strip() 
SPREADSHEET_NAME = "kalenderFCHP"
TEAM_ID = 107561

def sync_and_generate():
    local_tz = pytz.timezone("Europe/Stockholm")
    
    print("🚀 Startar synkronisering...")

    # 1. ANSLUT TILL GOOGLE SHEETS
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GOOGLE_JSON)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME).sheet1
    
    # 2. HÄMTA MATCHER FRÅN FOGIS (MED DUBBEL NYCKEL-SÄNDNING)
    date_from, date_to = "2026-01-01", "2026-12-31"
    # Vi lägger nyckeln direkt i URL:en för att garantera att den når fram
    url = f"https://forening-api.svenskfotboll.se/club/upcoming-games?from={date_from}&to={date_to}&w=3&subscription-key={FOGIS_API_KEY}"
    
    headers = {
        'Ocp-Apim-Subscription-Key': FOGIS_API_KEY,
        'Accept': 'application/json'
    }
    
    print(f"⏳ Hämtar matcher från FOGIS...")
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ FOGIS-fel ({response.status_code}): {response.text}")
        return

    games = response.json().get('games', [])
    prisoners_games = [g for g in games if g.get('homeTeamId') == TEAM_ID or g.get('awayTeamId') == TEAM_ID]
    print(f"✅ Hittade {len(prisoners_games)} matcher för Prisoners.")

    # 3. UPPDATERA ARKET
    all_rows = sheet.get_all_records()
    sheet_matches = {str(r.get('Matchnr')): i + 2 for i, r in enumerate(all_rows) if r.get('Matchnr')}

    for g in prisoners_games:
        m_nr = str(g.get('gameNumber'))
        datum = g.get('timeAsDateTime', '').split('T')[0]
        tid = g.get('timeAsDateTime', '').split('T')[1][:5] if 'T' in g.get('timeAsDateTime', '') else ''
        plats = g.get('venueName', 'Ej fastställt')
        desc = f"Match: {g.get('homeTeamName')} - {g.get('awayTeamName')}\nSerie: {g.get('competitionName')}"
        
        row = [datum, tid, "", plats, "Match", desc, m_nr]

        if m_nr in sheet_matches:
            sheet.update(f"A{sheet_matches[m_nr]}:G{sheet_matches[m_nr]}", [row])
        else:
            sheet.append_row(row)

    print("🎉 Allt klart! Kalkylarket är uppdaterat.")

if __name__ == "__main__":
    sync_and_generate()
