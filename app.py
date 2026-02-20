import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. ŞİFRE KORUMASI ---
if "password_correct" not in st.session_state:
    st.title("🔐 WBA KPI Paneli Girişi")
    
    # Geçerli şifreler listesi (Buraya istediğiniz kadar şifre ekleyebilirsiniz)
    GECERLI_SIFRELER = ["wbaajans2026", "Kpi_musteri123", "kpi-takip_Oliz26"]
    
    password = st.text_input("Lütfen Giriş Şifresini Yazın", type="password")
    
    if st.button("Giriş Yap"):
        if password in GECERLI_SIFRELER: # Şifre listede var mı kontrolü
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

# --- BURAYI DEĞİŞTİRİN ---
# 1. Adımda kopyaladığınız o uzun kodu buraya yapıştırın:
SHEET_ID = "1g_cxk9m6-IDIc3DQlazDVIS3VivnQmK3lWBuchO8WPc" 
TAB_NAME = "KPI"

try:
    client = get_ss_client()
    # Dosyayı ID ile açıyoruz (En güvenli yol)
    try:
        ss = client.open_by_key(SHEET_ID)
    except Exception as e:
        st.error(f"❌ HATA: Dosyaya erişilemedi. Lütfen ID'nin doğru olduğundan ve dosyanın 'kpi-bot@...' adresiyle paylaşıldığından emin olun.")
        st.info(f"Teknik Hata: {e}")
        st.stop()
        
    try:
        sheet = ss.worksheet(TAB_NAME)
    except:
        st.error(f"❌ HATA: Dosya açıldı ama içinde '{TAB_NAME}' adında bir sekme bulunamadı. Lütfen sekme adını 'KPI' yapın.")
        st.stop()

except Exception as e:
    st.error(f"⚠️ BAĞLANTI HATASI: {e}")
    st.stop()

def get_data():
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty:
        df['Hedef'] = pd.to_numeric(df['Hedef'], errors='coerce').fillna(0).astype(int)
        df['Tamamlanan'] = pd.to_numeric(df['Tamamlanan'], errors='coerce').fillna(0).astype(int)
    return df

# --- 3. DASHBOARD GÖRÜNÜMÜ ---
st.set_page_config(page_title="WBA KPI Dashboard", layout="wide")
st.title("🚀 WBA KPI Takip Dashboard")

df = get_data()

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
