import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. ŞİFRE VE YETKİLENDİRME ---
if "role" not in st.session_state:
    st.title("🔐 Ajans KPI Paneli Girişi")
    password = st.text_input("Lütfen Giriş Şifresini Yazın", type="password")
    
    if st.button("Giriş Yap"):
        if password == "admin-ajans": # SİZİN ŞİFRENİZ (Ekleme/Silme Yetkili)
            st.session_state.role = "admin"
            st.rerun()
        elif password == "musteri-ajans": # MÜŞTERİ ŞİFRESİ (Sadece İzleme)
            st.session_state.role = "client"
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

SHEET_ID = "BURAYA_ID_GELECEK" # Kendi ID'nizi buraya yapıştırın
TAB_NAME = "KPI"

def get_data():
    client = get_ss_client()
    ss = client.open_by_key(SHEET_ID)
    sheet = ss.worksheet(TAB_NAME)
    data = sheet.get_all_records()
    return pd.DataFrame(data), sheet

df, sheet_obj = get_data()
df['Hedef'] = pd.to_numeric(df['Hedef'], errors='coerce').fillna(0).astype(int)
df['Tamamlanan'] = pd.to_numeric(df['Tamamlanan'], errors='coerce').fillna(0).astype(int)

# --- 3. ARAYÜZ YAPILANDIRMASI ---
st.set_page_config(page_title="Ajans KPI Dashboard", layout="wide")

# Sekmeler: Dashboard ve Yönetim (Sadece admin görebilir)
if st.session_state.role == "admin":
    tab1, tab2 = st.tabs(["📊 KPI Dashboard", "⚙️ Yönetici Paneli"])
else:
    tab1 = st.container() # Müşteri sadece dashboard'u görür
    tab2 = None

# --- TAB 1: DASHBOARD ---
with tab1:
    st.title("🚀 Aylık KPI Performans Raporu")
    
    # Filtreler (Sidebar)
    st.sidebar.header("👁️ Görünüm Ayarları")
    secilen_isler = st.sidebar.multiselect(
        "Görüntülenecek İş Kalemleri", 
        options=df['Is_Kalemi'].tolist(), 
        default=df['Is_Kalemi'].tolist()
    )
    grafik_sayisi = st.sidebar.slider("Satır Başına Grafik", 1, 5, 3)

    df_filtered = df[df['Is_Kalemi'].isin(secilen_isler)]

    if not df_filtered.empty:
        rows = [df_filtered.iloc[i:i + grafik_sayisi] for i in range(0, df_filtered.shape[0], grafik_sayisi)]
        for row_df in rows:
            cols = st.columns(grafik_sayisi)
            for i, (index, row) in enumerate(row_df.iterrows()):
                with cols[i]:
                    hedef = int(row['Hedef'])
                    yapilan = int(row['Tamamlanan'])
                    yuzde = (yapilan / hedef * 100) if hedef > 0 else 0
                    bar_color = "red" if yuzde < 50 else "orange" if yuzde < 90 else "green"
                    
                    fig = go.Figure(go.Indicator(
                        mode = "gauge+number", value = yapilan,
                        title = {'text': f"<b>{row['Is_Kalemi']}</b>", 'font': {'size': 18}},
                        gauge = {'axis': {'range': [None, max(hedef, yapilan, 1)]}, 'bar': {'color': bar_color}}
                    ))
                    fig.update_layout(height=250, margin=dict(l=30, r=30, t=50, b=20))
                    st.plotly_chart(fig, use_container_width=True)
                    st.write(f"<p style='text-align: center;'>Hedef: {hedef}</p>", unsafe_allow_html=True)
    
    st.divider()
    st.subheader("📋 Veri Tablosu")
    st.dataframe(df_filtered, use_container_width=True, hide_index=True)

# --- TAB 2: YÖNETİCİ PANELİ (SADECE ADMİNE ÖZEL) ---
if tab2:
    with tab2:
        st.header("🛠️ İş Kalemi ve Hedef Yönetimi")
        
        # 1. YENİ İŞ KALEMİ EKLEME
        with st.expander("➕ Yeni İş Kalemi Ekle"):
            yeni_ad = st.text_input("İş Kalemi Adı (Örn: LinkedIn Video)")
            yeni_hedef = st.number_input("Aylık Hedef", min_value=0, value=10)
            if st.button("Listeye Ekle"):
                if yeni_ad and yeni_ad not in df['Is_Kalemi'].values:
                    sheet_obj.append_row([yeni_ad, yeni_hedef, 0])
                    st.success(f"'{yeni_ad}' başarıyla eklendi! Sayfayı yenileyin.")
                    st.rerun()
                else:
                    st.error("İsim boş olamaz veya zaten mevcut.")

        # 2. HEDEFLERİ GÜNCELLEME VEYA SİLME
        with st.expander("📝 Mevcutları Düzenle / Sil"):
            is_listesi = df['Is_Kalemi'].tolist()
            secilen_duzenle = st.selectbox("Düzenlenecek İş", is_listesi)
            
            # Seçilen satırın verilerini bul
            row_idx = df[df['Is_Kalemi'] == secilen_duzenle].index[0]
            current_target = int(df.at[row_idx, 'Hedef'])
            
            yeni_h = st.number_input("Hedefi Güncelle", value=current_target)
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Hedefi Kaydet"):
                    # Google Sheets'te satırı bul (Başlık satırı + index + 1)
                    sheet_obj.update_cell(row_idx + 2, 2, yeni_h)
                    st.success("Hedef güncellendi!")
                    st.rerun()
            with c2:
                if st.button("❌ Bu İş Kalemini Tamamen Sil", type="primary"):
                    sheet_obj.delete_rows(row_idx + 2)
                    st.warning("İş kalemi silindi.")
                    st.rerun()

        st.info("💡 Not: Burada yaptığınız değişiklikler anında Google Sheets'e yansır.")
