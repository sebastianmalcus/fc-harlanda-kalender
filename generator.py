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
    now_str = datetime.now(local_tz).strftime("%Y-%m-%d %H:%M:%S")
    print("🚀 Startar smart synkronisering med tidsjustering...")

    # ==========================================
    # 1. ANSLUT TILL GOOGLE SHEETS & HÄMTA CACHE
    # ==========================================
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(GOOGLE_JSON)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open(SPREADSHEET_NAME).sheet1
    
    all_rows = sheet.get_all_records()
    
    sheet_matches = {}
    for i, row in enumerate(all_rows):
        if str(row.get('Källa', '')).upper() == 'FOGIS' and row.get('Matchnr'):
            # Säkerhetsfix: Ta bort ev. apostrofer och inledande nollor för en skottsäker jämförelse
            safe_id = str(row['Matchnr']).replace("'", "").lstrip('0')
            sheet_matches[safe_id] = (i + 2, row)

    # ==========================================
    # 2. HÄMTA MATCHER FRÅN FOGIS
    # ==========================================
    date_from, date_to = "2026-01-01", "2026-12-31"
    url = f"https://forening-api.svenskfotboll.se/club/upcoming-games?from={date_from}&to={date_to}&w=3"
    
    headers = {
        'ApiKey': FOGIS_API_KEY,
        'Cache-Control': 'no-cache',
        'Accept': 'application/json'
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"❌ FOGIS-fel ({response.status_code}): {response.text}")
        return

    data = response.json()
    games = data.get('games', [])
    prisoners_games = [g for g in games if g.get('homeTeamId') == TEAM_ID or g.get('awayTeamId') == TEAM_ID]
    
    api_matches = {}
    for g in prisoners_games:
        safe_id = str(g.get('gameNumber', '')).lstrip('0')
        api_matches[safe_id] = g

    # ==========================================
    # 3. SYNKRONISERA OCH LOGGA FÖRÄNDRINGAR
    # ==========================================
    for safe_id, g in api_matches.items():
        m_nr_original = str(g.get('gameNumber', ''))
        # Tvinga textformat i Google Sheets med en inledande apostrof
        sheet_m_nr = f"'{m_nr_original}" 
        
        match_dt_str = g.get('timeAsDateTime', '')
        
        # Tidslogik: Samling 75 min innan, Slut 110 min efter
        if 'T' in match_dt_str and len(match_dt_str) >= 16:
            match_start_dt = datetime.strptime(match_dt_str[:16], "%Y-%m-%dT%H:%M")
            samling_dt = match_start_dt - timedelta(minutes=75)
            slut_dt = match_start_dt + timedelta(minutes=110)
            
            datum = samling_dt.strftime("%Y-%m-%d")
            tid = samling_dt.strftime("%H:%M")
            slut_tid = slut_dt.strftime("%H:%M")
            match_tid_str = match_start_dt.strftime("%H:%M")
        else:
            datum = match_dt_str.split('T')[0] if match_dt_str else ''
            tid = ''
            slut_tid = ''
            match_tid_str = 'Ej fastställd'

        plats = g.get('venueName', 'Ej fastställt')
        hemma = g.get('homeTeamName', '')
        borta = g.get('awayTeamName', '')
        
        desc = f"Match: {hemma} - {borta}\nMatchstart: {match_tid_str}"
        
        if safe_id in sheet_matches:
            row_idx, old_data = sheet_matches[safe_id]
            changes = []
            
            if str(old_data.get('Datum', '')) != datum:
                changes.append(f"Datum: {old_data.get('Datum', '')} -> {datum}")
            if str(old_data.get('Start', '')) != tid:
                changes.append(f"Samling: {old_data.get('Start', '')} -> {tid}")
            if str(old_data.get('Slut', '')) != slut_tid:
                changes.append(f"Slut: {old_data.get('Slut', '')} -> {slut_tid}")
            if str(old_data.get('Plats', '')) != plats:
                changes.append(f"Plats: {old_data.get('Plats', '')} -> {plats}")
                
            if changes or str(old_data.get('Beskrivning', '')) != desc:
                change_log = " | ".join(changes) if changes else "Beskrivning uppdaterad"
                print(f"🔄 Uppdaterar match {m_nr_original}: {change_log}")
                updated_row = [datum, tid, slut_tid, plats, "Match", desc, sheet_m_nr, "FOGIS", change_log, now_str, "TRUE"]
                sheet.update(f"A{row_idx}:K{row_idx}", [updated_row])
            elif str(old_data.get('I Kalender', '')).upper() != 'TRUE':
                print(f"🔄 Återaktiverar match {m_nr_original}")
                sheet.update_cell(row_idx, 9, "Återaktiverad från FOGIS") 
                sheet.update_cell(row_idx, 10, now_str) 
                sheet.update_cell(row_idx, 11, "TRUE")  
        else:
            print(f"➕ Lägger till ny match: {m_nr_original} (Samling {tid})")
            new_row = [datum, tid, slut_tid, plats, "Match", desc, sheet_m_nr, "FOGIS", "Ny match", now_str, "TRUE"]
            sheet.append_row(new_row)

    # 3b. Hitta inställda/borttagna matcher
    for safe_id, (row_idx, old_data) in sheet_matches.items():
        if safe_id not in api_matches and str(old_data.get('I Kalender', '')).upper() == 'TRUE':
            m_nr_original = str(old_data.get('Matchnr', ''))
            print(f"❌ Match {m_nr_original} finns ej i FOGIS längre. Markerar som FALSE.")
            sheet.update_cell(row_idx, 9, "Borttagen från FOGIS (Inställd)")
            sheet.update_cell(row_idx, 10, now_str)
            sheet.update_cell(row_idx, 11, "FALSE")

    # ==========================================
    # 4. SKAPA ICS-FILEN
    # ==========================================
    print("📅 Genererar kalenderfil...")
    final_rows = sheet.get_all_records()
    
    cal = Calendar()
    cal.add('prodid', '-//FC Harlanda//Fotbollskalender//SV')
    cal.add('version', '2.0')
    cal.add('x-wr-calname', 'FC Härlanda')
    
    for row in final_rows:
        try:
            i_kalender = str(row.get('I Kalender', '')).strip().upper()
            if i_kalender == 'FALSE':
                continue 

            datum_str = str(row.get('Datum', '')).strip()
            start_str = str(row.get('Start', '')).strip()
            
            if not datum_str or not start_str:
                continue
                
            start_dt = local_tz.localize(datetime.strptime(f"{datum_str} {start_str}", "%Y-%m-%d %H:%M"))
            
            slut_str = str(row.get('Slut', '')).strip()
            if slut_str:
                end_dt = local_tz.localize(datetime.strptime(f"{datum_str} {slut_str}", "%Y-%m-%d %H:%M"))
                if end_dt < start_dt:
                    end_dt += timedelta(days=1)
            else:
                end_dt = start_dt + timedelta(hours=2)

            event = Event()
            typ = str(row.get('Typ', 'Aktivitet'))
            plats = str(row.get('Plats', ''))
            beskrivning = str(row.get('Beskrivning', ''))
            
            event.add('summary', f"{typ}: {plats}")
            event.add('dtstart', start_dt)
            event.add('dtend', end_dt)
            event.add('location', plats)
            event.add('description', beskrivning)
            
            cal.add_component(event)
        except Exception as e:
            continue

    with open('kalender.ics', 'wb') as f:
        f.write(cal.to_ical())
    
    print("🎉 Allt klart! Logg uppdaterad och ny kalenderfil skapad.")

if __name__ == "__main__":
    sync_and_generate()
