# KI Invest Agenten

## Zweck

Eigenständiges Agentenprojekt für KI-Invest.

## Dieses Repository

/home/burgeragent/ki_invest_agenten

## Saubere Trennung

Dieses Projekt enthält Agentenlogik, Prompts, Konfiguration, Connectoren, Templates und lokal erzeugte Agentenreports.

Das Projekt ist getrennt vom Kernsystem KI-Invest.

## Externe Datenquellen

Fremdprojekte dürfen nur über definierte Connectoren gelesen werden.

## Regeln

- keine Finanzdaten im Repository speichern
- keine Depotdaten verändern
- keine Scoring-Dateien verändern
- keine Dateien außerhalb dieses Repositories überschreiben
- keine API-Schlüssel anzeigen
- kein git push ohne ausdrückliche Freigabe

## Erlaubt

- Agentenskripte erstellen
- Nachrichten abrufen
- lokale Reports unter reports/ erzeugen
- Logs unter logs/ erzeugen
- Connectoren für lesenden Zugriff erstellen
