import os
import json
import gspread
from google.oauth2.service_account import Credentials

def test_google_sheet():
    # --- KONFIGURATION ---
    GOOGLE_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON', '').strip() 
    SPREADSHEET_NAME = "kalenderFCHP"

    print("🚀 Startar test av Google Sheets-koppling...")

    if not GOOGLE_JSON:
        print("❌ FEL: Hittar ingen inloggningsnyckel (GOOGLE_CREDENTIALS_JSON) i Secrets.")
        return

    try:
        # 1. Logga in
        print("⏳ Loggar in hos Google...")
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_dict = json.loads(GOOGLE_JSON)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        print("✅ Inloggad hos Google!")

        # 2. Hitta arket
        print(f"⏳ Letar efter kalkylarket '{SPREADSHEET_NAME}'...")
        sheet = client.open(SPREADSHEET_NAME).sheet1
        print("✅ Hittade arket!")

        # 3. Skriv en ny rad (Testmatch)
        print("⏳ Försöker lägga till en rad längst ner...")
        test_rad = ["2026-12-24", "15:00", "17:00", "Nordpolen IP", "Träning", "Tomteträning", "TEST-123"]
        sheet.append_row(test_rad)
        print("✅ Lyckades lägga till raden!")

        # 4. Hitta raden vi just lade till och ändra texten (Testa uppdatering)
        print("⏳ Försöker uppdatera raden vi just skapade...")
        alla_rader = sheet.get_all_records()
        sista_raden_index = len(alla_rader) + 1 # +1 för att rubrikraden inte räknas med i get_all_records
        
        # Ändra texten i kolumn 6 (Beskrivning)
        sheet.update_cell(sista_raden_index, 6, "Tomteträning - UPPDATERAD AV ROBOTEN!")
        print("✅ Lyckades ändra texten!")
        
        print("🎉 ALLT FUNGERAR PERFEKT! Roboten har full makt över arket.")

    except gspread.exceptions.SpreadsheetNotFound:
        print(f"❌ FEL: Hittade inte kalkylarket '{SPREADSHEET_NAME}'.")
        print("   -> Lösning: Kolla att filen heter exakt så, och att roboten är inbjuden som redigerare!")
    except Exception as e:
        print(f"❌ ETT OVÄNTAT FEL UPPSTOD: {e}")

if __name__ == "__main__":
    test_google_sheet()
