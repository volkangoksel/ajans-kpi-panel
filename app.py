import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. ŞİFRE KORUMASI ---
if "password_correct" not in st.session_state:
    st.title("🔐 Ajans KPI Paneli Girişi")
    GECERLI_SIFRELER = ["wbaajans2026", "Kpi_musteri123", "kpi-takip_Oliz26"] # Şifrelerinizi buradan güncelleyebilirsiniz
    password = st.text_input("Lütfen Giriş Şifresini Yazın", type="password")
    if st.button("Giriş Yap"):
        if password in GECERLI_SIFRELER:
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("Hatalı şifre!")
    st.stop()

# --- 2. GOOGLE SHEETS BAĞLANTISI ---
def get_ss_client():
    creds_dict = st.secrets["gcp_service_account"]
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

SHEET_ID = "1g_cxk9m6-IDIc3DQlazDVIS3VivnQmK3lWBuchO8WPc" # Kendi ID'nizi buraya tekrar yapıştırın
TAB_NAME = "KPI"

def get_data():
    client = get_ss_client()
    ss = client.open_by_key(SHEET_ID)
    sheet = ss.worksheet(TAB_NAME)
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty:
        df['Hedef'] = pd.to_numeric(df['Hedef'], errors='coerce').fillna(0).astype(int)
        df['Tamamlanan'] = pd.to_numeric(df['Tamamlanan'], errors='coerce').fillna(0).astype(int)
    return df

# --- 3. DASHBOARD AYARLARI ---
st.set_page_config(page_title="Ajans KPI Dashboard", layout="wide")
st.title("🚀 Aylık KPI Performans Raporu")

# Veriyi çek
df = get_data()

# --- 4. FİLTRELEME VE DÜZEN (İstediğinizi Seçme Özelliği) ---
st.sidebar.header("📊 Görünüm Ayarları")
tum_isler = df['Is_Kalemi'].tolist()
secilen_isler = st.sidebar.multiselect(
    "Görüntülenecek İş Kalemlerini Seçin", 
    options=tum_isler, 
    default=tum_isler
)

# Her satırda kaç grafik olsun? (3 veya 4 idealdir)
grafik_sayisi_basi_satir = st.sidebar.slider("Satır Başına Grafik Sayısı", 1, 5, 3)

# Seçilenlere göre filtrele
df_filtered = df[df['Is_Kalemi'].isin(secilen_isler)]

# --- 5. IZGARA (GRID) YAPISI ---
if not df_filtered.empty:
    # Grafiklerin alt alta kaç satır olacağını hesapla
    rows = [df_filtered.iloc[i:i + grafik_sayisi_basi_satir] for i in range(0, df_filtered.shape[0], grafik_sayisi_basi_satir)]
    
    for row_df in rows:
        cols = st.columns(grafik_sayisi_basi_satir)
        for i, (index, row) in enumerate(row_df.iterrows()):
            hedef = int(row['Hedef'])
            yapilan = int(row['Tamamlanan'])
            yuzde = (yapilan / hedef * 100) if hedef > 0 else 0
            
            # Renkler
            bar_color = "red" if yuzde < 50 else "orange" if yuzde < 90 else "green"
            
            with cols[i]:
                fig = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = yapilan,
                    title = {'text': f"<b>{row['Is_Kalemi']}</b>", 'font': {'size': 18}},
                    gauge = {
                        'axis': {'range': [None, max(hedef, yapilan, 1)]},
                        'bar': {'color': bar_color},
                        'steps': [{'range': [0, hedef], 'color': "#333" if st.get_option("theme.base") == "dark" else "#eee"}]
                    }
                ))
                fig.update_layout(height=280, margin=dict(l=30, r=30, t=50, b=20))
                st.plotly_chart(fig, use_container_width=True)
                st.write(f"<p style='text-align: center; font-size: 16px;'>Hedef: <b>{hedef}</b> | Kalan: <b>{max(0, hedef-yapilan)}</b></p>", unsafe_allow_html=True)
else:
    st.info("Lütfen görüntülemek için soldan bir iş kalemi seçin.")

st.divider()
st.subheader("📋 Detaylı Liste")
st.dataframe(df_filtered, use_container_width=True, hide_index=True)
