import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import os
from dotenv import load_dotenv
from google import genai

# --- SETUP & KONFIGURATION ---
# Das muss ganz oben stehen, um die Seite breit zu machen
st.set_page_config(page_title="KI Börsen-Dashboard", layout="wide")

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("FEHLER: Konnte den Gemini API-Key nicht in der .env Datei finden.")
    st.stop()

client = genai.Client(api_key=api_key)


# --- FUNKTIONEN (Mit Caching, damit es schnell lädt) ---
def berechne_rsi(daten_reihe, zeitraum=14):
    delta = daten_reihe.diff()
    gewinn = delta.where(delta > 0, 0)
    verlust = -delta.where(delta < 0, 0)
    avg_gewinn = gewinn.rolling(window=zeitraum, min_periods=1).mean()
    avg_verlust = verlust.rolling(window=zeitraum, min_periods=1).mean()
    rs = avg_gewinn / avg_verlust
    rsi = 100 - (100 / (1 + rs))
    return rsi


@st.cache_data(ttl=3600)  # Speichert die Daten für 1 Stunde im Zwischenspeicher
def lade_daten(ticker):
    aktie = yf.Ticker(ticker)
    daten = aktie.history(period="6mo")

    if not daten.empty and len(daten) >= 50:
        daten['SMA_20'] = daten['Close'].rolling(window=20).mean()
        daten['SMA_50'] = daten['Close'].rolling(window=50).mean()
        daten['RSI_14'] = berechne_rsi(daten['Close'], 14)
    return daten, aktie.news


def analysiere_news_mit_ki(asset_name, news_titel):
    if not news_titel:
        return "Keine Nachrichten vorhanden."

    prompt = f"""
    Du bist ein erfahrener Finanzanalyst. Hier sind die neuesten Schlagzeilen zum Basiswert: {asset_name}.
    Schlagzeilen:
    {news_titel}
    Bitte schreibe einen prägnanten Absatz auf Deutsch. Analysiere, ob die Stimmung positiv, negativ oder neutral für den Kurs ist und warum.
    """
    try:
        antwort = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        return antwort.text.strip()
    except Exception as e:
        return f"Fehler bei KI-Analyse: {e}"


# --- UI / DASHBOARD AUFBAU ---
st.title("📈 KI-Börsen-Dashboard")
st.markdown("Analysiere Märkte mit Technischer Analyse und Google Gemini KI.")

# Seitenleiste für die Auswahl
st.sidebar.header("Einstellungen")
assets = {"DAX": "^GDAXI", "WTI Öl": "CL=F", "Gold": "GC=F"}
auswahl = st.sidebar.selectbox("Wähle einen Basiswert:", list(assets.keys()))
ticker_symbol = assets[auswahl]

st.header(f"Analyse für {auswahl}")

with st.spinner('Lade Daten und befrage die KI...'):
    daten, news = lade_daten(ticker_symbol)

    if daten.empty:
        st.error("Fehler beim Laden der Kursdaten.")
        st.stop()

    aktueller_kurs = daten['Close'].iloc[-1]
    sma20 = daten['SMA_20'].iloc[-1]
    sma50 = daten['SMA_50'].iloc[-1]
    rsi = daten['RSI_14'].iloc[-1]

    # 1. Metriken anzeigen (die schönen Boxen oben)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Aktueller Kurs", f"{aktueller_kurs:.2f}")
    col2.metric("SMA 20", f"{sma20:.2f}")
    col3.metric("SMA 50", f"{sma50:.2f}")
    col4.metric("RSI 14", f"{rsi:.2f}")

    # 2. Interaktiver Chart mit Plotly
    st.subheader("Kursverlauf (Interaktiv)")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daten.index, y=daten['Close'], mode='lines', name='Kurs', line=dict(color='white')))
    fig.add_trace(
        go.Scatter(x=daten.index, y=daten['SMA_20'], mode='lines', name='SMA 20', line=dict(color='blue', dash='dash')))
    fig.add_trace(
        go.Scatter(x=daten.index, y=daten['SMA_50'], mode='lines', name='SMA 50', line=dict(color='red', dash='dash')))

    fig.update_layout(height=500, margin=dict(l=0, r=0, t=0, b=0), template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    # 3. Technische Prognose
    st.subheader("🤖 Technische Auswertung")
    aufwaertstrend = aktueller_kurs > sma20 and sma20 > sma50
    abwaertstrend = aktueller_kurs < sma20 and sma20 < sma50

    if aufwaertstrend and rsi >= 70:
        st.warning("⚠️ **CHANCE/RISIKO:** Aufwärtstrend intakt, aber extrem 'überkauft'. Hohes Risiko für Rücksetzer.")
    elif aufwaertstrend:
        st.success("✅ **CHANCE/RISIKO:** Guter Aufwärtstrend. Moderates Risiko, Potenzial für weitere Gewinne.")
    elif abwaertstrend and rsi <= 30:
        st.warning("⚠️ **CHANCE/RISIKO:** Abwärtstrend, aber 'überverkauft'. Rebound möglich, aber riskant.")
    elif abwaertstrend:
        st.error("🚨 **CHANCE/RISIKO:** Klarer Abwärtstrend. Risiko für weitere Verluste ist hoch.")
    else:
        st.info("ℹ️ **CHANCE/RISIKO:** Seitwärtsphase. Abwarten auf klare Signale.")

    # 4. News & KI
    st.subheader("📰 KI-Fundamentalanalyse")
    gesammelte_titel = ""

    if news:
        for artikel in news[:3]:
            titel = artikel.get('title')
            if not titel and 'content' in artikel:
                titel = artikel['content'].get('title')
            if titel:
                gesammelte_titel += f"- {titel}\n"

        st.markdown("**Aktuelle Schlagzeilen:**")
        st.text(gesammelte_titel)

        st.markdown("**Gemini Analyse:**")
        ki_analyse = analysiere_news_mit_ki(auswahl, gesammelte_titel)
        st.write(ki_analyse)
    else:
        st.write("Keine aktuellen Nachrichten gefunden.")