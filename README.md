# 🗺️ GPS Tracker Map — Custom Integration per Home Assistant

Visualizza gli spostamenti del tuo telefono degli ultimi N giorni su una mappa interattiva **completamente gratuita** (OpenStreetMap + Leaflet).

---

## ✨ Funzionalità

- **Mappa dark** con percorso colorato in base alla velocità
- **Statistiche**: distanza totale, durata, punti GPS, velocità massima
- **Rilevamento soste** automatico con marker gialli
- **Timeline** cronologica cliccabile (centra la mappa sul punto)
- **Filtro per giorno** (Oggi / Ieri / altri giorni / Tutti)
- **Refresh automatico** configurabile in minuti
- Legenda velocità (a piedi / lento / auto / veloce)

---

## 📋 Prerequisiti

| Cosa | Note |
|------|------|
| **Home Assistant OS** | Versione 2023.x o superiore |
| **App HA Companion** | [Android](https://play.google.com/store/apps/details?id=io.homeassistant.companion.android) o [iOS](https://apps.apple.com/app/home-assistant/id1099568401) |
| **Recorder** attivo | Abilitato di default in HA |

---

## 🚀 Installazione

### Passo 1 — Copia i file

Copia la cartella `custom_components/gps_tracker_map/` nella cartella `/config/custom_components/` del tuo Home Assistant.

Struttura finale:
```
/config/
└── custom_components/
    └── gps_tracker_map/
        ├── __init__.py
        ├── manifest.json
        ├── config_flow.py
        ├── const.py
        ├── translations/
        │   └── it.json
        └── panel/
            └── index.html
```

### Passo 2 — Riavvia Home Assistant

**Impostazioni → Sistema → Riavvia**

### Passo 3 — Aggiungi l'integrazione

1. Vai su **Impostazioni → Dispositivi e servizi → Aggiungi integrazione**
2. Cerca **"GPS Tracker Map"**
3. Seleziona il tuo `device_tracker` (es: `device_tracker.pixel_8`)
4. Imposta i giorni di storico desiderati

### Passo 4 — Configura il pannello

Dopo l'installazione apparirà **"GPS Tracker"** nella sidebar di HA.  
Al primo accesso ti chiederà:

1. **URL di HA** → pre-compilato automaticamente
2. **Long-Lived Access Token** → vedi sotto come generarlo
3. **Entity ID** → il device_tracker del tuo telefono
4. **Giorni** e **intervallo di refresh**

---

## 🔑 Come generare un Long-Lived Access Token

1. Clicca sulla tua **foto profilo** in basso a sinistra in HA
2. Scorri fino a **"Token di accesso di lunga durata"**
3. Clicca **"Crea token"**, dai un nome (es: "GPS Tracker Map")
4. **Copia subito il token** (non verrà mostrato di nuovo)
5. Incollalo nelle impostazioni del pannello

---

## 📱 Configurare l'App HA Companion

Affinché la posizione venga inviata a HA:

1. Apri l'app → **Impostazioni app → Sensori**
2. Abilita **"Posizione"** (Location)
3. Scegli la precisione desiderata (consigliato: Alta precisione)
4. L'entity `device_tracker.nome_telefono` comparirà in HA automaticamente

---

## 🎨 Legenda colori percorso

| Colore | Velocità |
|--------|----------|
| 🟣 Viola | < 5 km/h (a piedi) |
| 🟢 Verde | < 30 km/h (bici/traffico) |
| 🟡 Giallo | < 80 km/h (auto) |
| 🔴 Rosso | > 80 km/h (autostrada) |

---

## 🔧 Risoluzione problemi

| Problema | Soluzione |
|----------|-----------|
| Entity non trovata | Verifica che l'app companion sia connessa e abbia inviato almeno una posizione |
| Token non valido | Rigenera il token dal profilo HA |
| Nessun punto GPS | Il recorder deve essere attivo e aver raccolto dati per il periodo selezionato |
| Errore HTTP 401 | Token scaduto o errato |

---

## 📂 Struttura progetto

```
ha-gps-tracker/
├── README.md                          ← questo file
└── custom_components/
    └── gps_tracker_map/
        ├── __init__.py               ← setup, registra pannello e static files
        ├── manifest.json             ← metadati integrazione
        ├── config_flow.py            ← UI configurazione in HA
        ├── const.py                  ← costanti
        ├── translations/it.json      ← traduzioni italiane
        └── panel/index.html          ← mappa Leaflet (OpenStreetMap)
```
