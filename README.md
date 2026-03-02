# ⚽ FC Härlanda Prisoners - Automatisk Kalender

Detta projekt håller FC Härlanda Prisoners lagkalender ständigt uppdaterad. Den synkroniserar automatiskt officiella matcher från Svenska Fotbollförbundets (SvFF) system FOGIS med ett Google Kalkylark, där vi även kan lägga in egna träningar. Slutresultatet blir en prenumererbar `.ics`-fil som alla spelare kan ha direkt i mobilen.

---

## 📱 För Spelare: Så här prenumererar du på kalendern

Kopiera länken nedan och följ instruktionerna för din telefon. *(Obs: Klicka inte på länken, den ska kopieras och klistras in i kalender-appen!)*

**Kalenderlänk:** `https://raw.githubusercontent.com/sebastianmalcus/fc-harlanda-kalender/main/kalender.ics`
*(Ändra `sebastianmalcus` och repots namn om länken ovan inte stämmer exakt)*

### 🍎 iPhone / iOS
1. Gå till **Inställningar** i telefonen.
2. Välj **Kalender** -> **Konton** -> **Lägg till konto**.
3. Välj **Annat** längst ner.
4. Välj **Lägg till prenumererad kalender**.
5. Klistra in länken ovan i fältet "Server" och klicka på **Nästa**.
6. Klicka på **Spara**. Klart!

### 🤖 Android / Google Kalender
*(Detta görs enklast via en dator)*
1. Öppna [Google Kalender](https://calendar.google.com) i webbläsaren.
2. I vänstermenyn, leta upp rubriken **Andra kalendrar** och klicka på **Plus-tecknet (+)**.
3. Välj **Från webbadress**.
4. Klistra in länken ovan och klicka på **Lägg till kalender**.
5. Öppna kalender-appen i din telefon, gå till inställningar och se till att den nya kalendern är ibockad och synkroniserad.

---

## 📝 För Administratörer: Så hanterar du kalkylarket

Kalkylarket (`kalenderFCHP`) är "hjärnan" i systemet. Roboten läser av detta ark var sjätte timme för att bygga kalendern.

### Lägga till en manuell träning/aktivitet
För att lägga till något som inte finns i FOGIS (t.ex. en träning eller lagfest):
1. Skrolla längst ner i kalkylarket till en tom rad.
2. Fyll i **Datum** (`ÅÅÅÅ-MM-DD`), **Start** (`HH:MM`), **Plats** och **Typ** (t.ex. "Träning").
3. **Matchnr** och **Källa** lämnar du helt tomma.
4. Sätt **I Kalender** till `TRUE`.
5. Nästa gång roboten körs dyker aktiviteten upp i allas telefoner!

### Ta bort/ställa in en aktivitet
* **Manuella händelser:** Skriv `FALSE` i kolumnen **I Kalender** (eller radera raden helt).
* **FOGIS-matcher:** Du behöver inte göra något! Om en match ställs in eller flyttas i FOGIS kommer roboten automatiskt att märka det, uppdatera tiderna, eller sätta `I Kalender` till `FALSE` om matchen helt utgår.

---

## ⚙️ Teknisk Dokumentation & Metoder

Systemet drivs av ett Python-skript (`generator.py`) som körs automatiskt via **GitHub Actions**.

### 1. Autentisering
* **FOGIS API:** Använder SvFF Club Football API. Efter mycket felsökning mot Azure API Management fastställdes det att headern `ApiKey` krävs för lyckade anrop, trots att standarddokumentationen ibland föreslår annat.
* **Google Sheets API:** Autentiseras via ett Google Cloud Service Account vars JSON-nyckel förvaras säkert i GitHub Secrets.

### 2. Synk-logik & Cache-hantering
För att undvika dubbletter och hantera uppdateringar utan att skriva över manuell data använder vi en "Soft Delete"-logik:
1. **Lokal Cache:** Skriptet laddar ner alla befintliga rader från Google Sheets och indexerar alla rader där `Källa = FOGIS` med `Matchnr` som nyckel. För att undvika formateringsproblem i Sheets (försvinnande nollor) rensas alltid inledande nollor bort i koden innan jämförelse.
2. **Jämförelse:** Skriptet hämtar aktuella matcher från FOGIS och jämför med vår lokala cache. 
   * Om datum, tid eller plats skiljer sig uppdateras den specifika raden.
   * Om ett matchnummer från FOGIS saknas i Sheets läggs det till som en ny rad.
3. **Soft Delete:** Om ett matchnummer finns i Sheets men har försvunnit från FOGIS (inställd match), raderas inte raden. Istället sätts flaggan `I Kalender` till `FALSE` och ändringen loggas. Detta bevarar historiken utan att störa spelarnas kalendrar.



### 3. Tidsjusteringar för Matcher
FOGIS API levererar endast avsparkstiden. För att optimera kalendern för spelarna beräknar skriptet automatiskt nya tider:
* **Starttid (Samling):** Sätts automatiskt till 75 minuter *före* avspark.
* **Sluttid:** Sätts automatiskt till 110 minuter *efter* avspark (90 min match + 20 min paus).
* Avsparkstiden skrivs istället tydligt ut i fältet `Beskrivning`.
