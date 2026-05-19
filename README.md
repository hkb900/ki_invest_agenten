# KI Invest Agenten

Eigenständiges Agentenprojekt für KI-Invest.

## Ziel

Automatisierte Agenten für:

- Finanznachrichten
- Depotkommentare
- externe Reviews
- HTML-Reports
- spätere OpenClaw-Steuerung

## Architektur

Dieses Repository bleibt getrennt vom Kernsystem.

- Agentenlogik: `~/ki_invest_agenten`
- Kernsystem: eigenes externes Projekt
- Zugriff auf externe Daten nur über Connectoren
- lokale Agentenreports unter `reports/`

## Grundregel

Agenten dürfen lesen, strukturieren und berichten.

Sie dürfen keine Depotdaten, Scoring-Dateien oder Kernsystemdateien verändern.

