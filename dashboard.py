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
    aktie = yf.Ticker(ticker)
    daten = aktie.history(period="6mo")
    if not daten.empty:
        daten['SMA_20'] = daten['Close'].rolling(window=20).mean()
        daten['SMA_50'] = daten['Close'].rolling(window=50).mean()
        daten['RSI_14'] = berechne_rsi(daten['Close'], 14)
    return daten, aktie.news

def ki_auswertung(asset_name, news_text):
    prompt = f"Analysiere als Finanzexperte diese Schlagzeilen für {asset_name} (max 3 Sätze, Deutsch): {news_text}"
    try:
        # Kleiner Puffer für die API
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
    kurs = daten['Close'].iloc[-1]
    rsi = daten['RSI_14'].iloc[-1]
    col1, col2, col3 = st.columns(3)
    col1.metric("Aktueller Kurs", f"{kurs:.2f}")
    col2.metric("RSI (Momentum)", f"{rsi:.2f}")
    col3.metric("Trend", "Bullisch" if kurs > daten['SMA_50'].iloc[-1] else "Bearisch")

    # 2. Interaktiver Chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daten.index, y=daten['Close'], name="Kurs", line=dict(color='white')))
    fig.add_trace(go.Scatter(x=daten.index, y=daten['SMA_20'], name="SMA 20", line=dict(color='cyan', dash='dot')))
    fig.add_trace(go.Scatter(x=daten.index, y=daten['SMA_50'], name="SMA 50", line=dict(color='magenta', dash='dot')))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)

 # 3. Schlagzeilen (Klickbar & Erweitert)
    st.subheader(f"📰 Top Schlagzeilen für {auswahl}")
    text_fuer_ki = ""
    
    if news_liste:
        for n in news_liste[:10]:
            # 1. Titel extrem sicher auslesen
            t = n.get('title')
            if not t and isinstance(n.get('content'), dict):
                t = n['content'].get('title')
            t = t or "Kein Titel verfügbar"

            # 2. Link extrem sicher auslesen (Der Bugfix!)
            l = n.get('link')
            if not l and isinstance(n.get('content'), dict):
                click_info = n['content'].get('clickThroughUrl')
                # Wir prüfen extra, ob click_info WIRKLICH ein Dictionary ist und nicht None
                if isinstance(click_info, dict):
                    l = click_info.get('url')
            l = l or "https://finance.yahoo.com"
            
            st.markdown(f"- [{t}]({l})")
            text_fuer_ki += f"{t}. "
    else:
        st.info("Keine aktuellen Nachrichten gefunden.")

    st.divider()

    def ki_auswertung(asset_name, news_text):
    # HIER IST DER NEUE PROMPT (Die Arbeitsanweisung für die KI)
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
        # Kleiner Puffer für die API
        time.sleep(1) 
        # Wir nutzen das schnelle Flash-Modell
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
    kurs = daten['Close'].iloc[-1]
    rsi = daten['RSI_14'].iloc[-1]
    col1, col2, col3 = st.columns(3)
    col1.metric("Aktueller Kurs", f"{kurs:.2f}")
    col2.metric("RSI (Momentum)", f"{rsi:.2f}")
    col3.metric("Trend", "Bullisch" if kurs > daten['SMA_50'].iloc[-1] else "Bearisch")

    # 2. Interaktiver Chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daten.index, y=daten['Close'], name="Kurs", line=dict(color='white')))
    fig.add_trace(go.Scatter(x=daten.index, y=daten['SMA_20'], name="SMA 20", line=dict(color='cyan', dash='dot')))
    fig.add_trace(go.Scatter(x=daten.index, y=daten['SMA_50'], name="SMA 50", line=dict(color='magenta', dash='dot')))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=0,r=0,t=0,b=0))
    st.plotly_chart(fig, use_container_width=True)

    # 3. Schlagzeilen (Klickbar & Erweitert)
    st.subheader(f"📰 Top Schlagzeilen für {auswahl}")
    text_fuer_ki = ""
    
    if news_liste:
        for n in news_liste[:10]:
            t = n.get('title')
            if not t and isinstance(n.get('content'), dict):
                t = n['content'].get('title')
            t = t or "Kein Titel verfügbar"

            l = n.get('link')
            if not l and isinstance(n.get('content'), dict):
                click_info = n['content'].get('clickThroughUrl')
                if isinstance(click_info, dict):
                    l = click_info.get('url')
            l = l or "https://finance.yahoo.com"
            
            st.markdown(f"- [{t}]({l})")
            text_fuer_ki += f"{t}. "
    else:
        st.info("Keine aktuellen Nachrichten gefunden.")

    st.divider()

   def ki_auswertung(asset_name, news_text):
                    # Ab hier MUSS alles eingerückt sein (4 Leerzeichen)
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
                        # Auch dieses try/except muss eingerückt sein
                        time.sleep(1) 
                        antwort = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                        return antwort.text.strip()
                    except Exception as e:
                        return f"KI-Analyse aktuell nicht verfügbar: {e}"
