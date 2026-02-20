import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. ŞİFRE KORUMASI ---
# Müşterinin girmesi için şifre ekranı
if "password_correct" not in st.session_state:
    st.title("🔐 Ajans KPI Paneli Girişi")
    password = st.text_input("Lütfen Giriş Şifresini Yazın", type="password")
    if st.button("Giriş Yap"):
        if password == "ajans2024": # BURAYI İSTEDİĞİN ŞİFREYLE DEĞİŞTİR
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("Hatalı şifre!")
    st.stop()

# --- 2. GOOGLE SHEETS BAĞLANTISI (BULUT SÜRÜMÜ) ---
def get_ss_client():
    # Bu kısım bilgisayardaki creds.json yerine 
    # Streamlit Cloud üzerindeki "Secrets" ayarlarını okur
    creds_dict = st.secrets["gcp_service_account"]
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

SHEET_NAME = "KPI_Takip_Sistemi" # Google Sheet dosyanızın adı

try:
    client = get_ss_client()
    sheet = client.open(SHEET_NAME).worksheet("KPI")
except Exception as e:
    st.error(f"Hata: Sayfaya erişilemedi. Lütfen Secrets ayarlarını kontrol edin.")
    st.stop()

def get_data():
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty:
        df['Hedef'] = pd.to_numeric(df['Hedef'], errors='coerce').fillna(0).astype(int)
        df['Tamamlanan'] = pd.to_numeric(df['Tamamlanan'], errors='coerce').fillna(0).astype(int)
    return df

# --- 3. DASHBOARD GÖRÜNÜMÜ ---
st.set_page_config(page_title="Ajans KPI Dashboard", layout="wide")
st.title("🚀 Aylık KPI Performans Raporu")

df = get_data()

# KPI Kartları
cols = st.columns(len(df))
for i, row in df.iterrows():
    hedef = int(row['Hedef'])
    yapilan = int(row['Tamamlanan'])
    yuzde = (yapilan / hedef * 100) if hedef > 0 else 0
    bar_color = "red" if yuzde < 50 else "orange" if yuzde < 90 else "green"
    
    with cols[i]:
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = yapilan,
            title = {'text': f"<b>{row['Is_Kalemi']}</b>", 'font': {'size': 16}},
            gauge = {
                'axis': {'range': [None, max(hedef, yapilan, 1)]},
                'bar': {'color': bar_color},
                'steps': [{'range': [0, hedef], 'color': "#eeeeee"}]
            }
        ))
        fig.update_layout(height=250, margin=dict(l=20, r=20, t=50, b=20))
        st.plotly_chart(fig, use_container_width=True)
        st.write(f"<p style='text-align: center;'>Hedef: {hedef}</p>", unsafe_allow_html=True)

st.divider()
st.subheader("📋 Detaylı Liste")
st.dataframe(df, use_container_width=True, hide_index=True)
