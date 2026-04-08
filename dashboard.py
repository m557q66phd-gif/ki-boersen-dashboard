import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import os
import time
from dotenv import load_dotenv
from google import genai

# --- SETUP ---
st.set_page_config(page_title="Profi KI-Börsen-Dashboard", layout="wide")

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("API-Key fehlt! Bitte in der .env Datei oder den Secrets ergänzen.")
    st.stop()

client = genai.Client(api_key=api_key)

# --- FUNKTIONEN ---
def berechne_rsi(daten_reihe, zeitraum=14):
    delta = daten_reihe.diff()
    gewinn = delta.where(delta > 0, 0)
    verlust = -delta.where(delta < 0, 0)
    avg_gewinn = gewinn.rolling(window=zeitraum, min_periods=1).mean()
    avg_verlust = verlust.rolling(window=zeitraum, min_periods=1).mean()
    rs = avg_gewinn / avg_verlust
    rsi = 100 - (100 / (1 + rs))
    return rsi

@st.cache_data(ttl=600)
def lade_marktdaten(ticker):
    # Wir übergeben KEINE eigene Session mehr. yfinance nutzt jetzt
    # automatisch das neue curl_cffi Paket im Hintergrund!
    aktie = yf.Ticker(ticker)
    daten = aktie.history(period="6mo")
    
    if not daten.empty:
        daten['SMA_20'] = daten['Close'].rolling(window=20).mean()
        daten['SMA_50'] = daten['Close'].rolling(window=50).mean()
        daten['RSI_14'] = berechne_rsi(daten['Close'], 14)
        
    return daten, aktie.news

def ki_auswertung(asset_name, news_text):
    prompt = f"""
    Du bist ein präziser Finanzexperte. Analysiere diese aktuellen Schlagzeilen für {asset_name}:
    {news_text}
    
    Bitte antworte exakt in diesem Format auf Deutsch:
    
    **📰 Kurz-Zusammenfassung der Nachrichten:**
    (Fasse hier in 2 bis 3 extrem kurzen Stichpunkten zusammen, was die Hauptthemen dieser Artikel sind)
    
    **🎯 Gesamtauswertung & Fazit:**
    (Gebe in 1 bis maximal 2 Sätzen dein Fazit ab: Ist die Stimmung eher bullisch, bearisch oder neutral für den Preis und warum?)
    """
    try:
        time.sleep(1) 
        antwort = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return antwort.text.strip()
    except Exception as e:
        return f"KI-Analyse aktuell nicht verfügbar: {e}"

# --- DASHBOARD UI ---
st.title("🚀 KI-Börsen-Zentrale")

# Seitenleiste
assets = {"DAX": "^GDAXI", "WTI Öl": "CL=F", "Gold": "GC=F", "Bitcoin": "BTC-USD", "S&P 500": "^GSPC"}
auswahl = st.sidebar.selectbox("Basiswert wählen:", list(assets.keys()))
ticker = assets[auswahl]

# Daten laden
daten, news_liste = lade_marktdaten(ticker)

if daten.empty:
    st.error("Daten konnten nicht geladen werden.")
else:
    # 1. Metriken
    kurs = daten['Close'].iloc
