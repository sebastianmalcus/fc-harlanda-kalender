import os
import requests

def test_fogis_api():
    FOGIS_API_KEY = os.getenv('FOGIS_API_KEY', '').strip()
    TEAM_ID = 107561 # Vårt nuvarande ID för Prisoners
    
    print("🚀 Startar test av FOGIS API...")
    
    if not FOGIS_API_KEY:
        print("❌ FEL: FOGIS_API_KEY saknas i Secrets.")
        return
        
    date_from = "2026-01-01"
    date_to = "2026-12-31"
    url = f"https://forening-api.svenskfotboll.se/club/upcoming-games?from={date_from}&to={date_to}&w=3"
    
    headers = {
        'Ocp-Apim-Subscription-Key': FOGIS_API_KEY,
        'Accept': 'application/json'
    }
    
    print(f"⏳ Anropar FOGIS API från {date_from} till {date_to}...")
    response = requests.get(url, headers=headers)
    
    print(f"HTTP Status: {response.status_code}")
    
    if response.status_code != 200:
        print(f"❌ Fel från FOGIS: {response.text}")
        return
        
    try:
        data = response.json()
        games = data.get('games', [])
        print(f"✅ Fick svar! Hittade totalt {len(games)} matcher för hela FC Härlanda.")
        
        if len(games) > 0:
            print("\n🔍 Analyserar de 3 första matcherna i klubben för att hitta lag-ID:")
            for g in games[:3]:
                print(f"- {g.get('homeTeamName')} vs {g.get('awayTeamName')}")
                print(f"  Hemma-ID: {g.get('homeTeamId')} | Borta-ID: {g.get('awayTeamId')}")
                
        # Testa om Prisoners har några matcher alls med vårt nuvarande ID
        prisoners_games = [g for g in games if g.get('homeTeamId') == TEAM_ID or g.get('awayTeamId') == TEAM_ID]
        print(f"\n⚽ Antal matcher som matchar Team ID {TEAM_ID} (Prisoners): {len(prisoners_games)}")
        
        if len(games) > 0 and len(prisoners_games) == 0:
            print("⚠️ Hela klubben har matcher, men inga för Prisoners! Vi använder nog fel Team-ID.")
            
    except Exception as e:
        print(f"❌ Kunde inte tolka svaret från FOGIS: {e}")

if __name__ == "__main__":
    test_fogis_api()
