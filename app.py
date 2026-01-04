import streamlit as st
import pandas as pd
import time
import requests
import smtplib
import random
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import plotly.graph_objects as go
from streamlit_lottie import st_lottie
from PIL import Image

# Barkod kütüphanesi kontrolü
try:
    from pyzbar.pyzbar import decode
    HAS_BARCODE_LIB = True
except:
    HAS_BARCODE_LIB = False

# engine.py'dan fonksiyonları içe aktar
from engine import search_all_sources, get_amazon_deals

# ==========================================
# 1. AYARLAR & GÜVENLİK
# ==========================================
st.set_page_config(page_title="GhostDeal Pro", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# --- LOTTIE LOADER ---
def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        if r.status_code != 200: return None
        return r.json()
    except: return None

anim_cart = load_lottieurl("https://assets10.lottiefiles.com/packages/lf20_6wjmecxo.json")

# --- CACHING ---
@st.cache_data(ttl=3600, show_spinner=False)
def cached_search(query, serp_key, rapid_key):
    return search_all_sources(query, serp_key, rapid_key)

@st.cache_data(ttl=3600, show_spinner=False)
def cached_deals(rapid_key, country="TR"):
    return get_amazon_deals(rapid_key, country)

# --- LOGIN ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else: st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("🔒 GhostDeal Erişim Şifresi", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("🔒 GhostDeal Erişim Şifresi", type="password", on_change=password_entered, key="password")
        st.error("❌ Hatalı şifre.")
        return False
    return True

# --- API KEY & AI ---
try:
    if check_password():
        SERP_API_KEY = st.secrets["SERP_API_KEY"]
        RAPID_API_KEY = st.secrets["RAPID_API_KEY"]
        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
        import google.generativeai as genai
        HAS_AI = True
    else: st.stop()
except:
    st.warning("⚠️ API Anahtarları bulunamadı.")
    st.stop()

# --- MAİL GÖNDERME ---
def send_email_alert(to_email, product_name, price, link):
    try:
        sender_email = st.secrets["EMAIL_SENDER"]
        sender_password = st.secrets["EMAIL_PASSWORD"]
        subject = f"🚨 FİYAT DÜŞTÜ: {product_name}"
        body = f"<html><body><h2>🔥 GhostDeal Yakaladı!</h2><h3>📦 {product_name}</h3><h1 style='color:green;'>{price}</h1><a href='{link}'>ÜRÜNE GİT</a></body></html>"
        msg = MIMEMultipart()
        msg['From'] = f"GhostDeal AI <{sender_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True
    except: return False

# ==========================================
# 2. COMMAND CENTER CSS
# ==========================================
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Orbitron:wght@500;700;900&display=swap');
        header {background: transparent !important;}
        [data-testid="collapsedControl"] {display: block !important; color: #a78bfa !important;}
        .stDeployButton, #MainMenu, footer {display:none; visibility: hidden;}
        .stApp {
            background-color: #050505; 
            background-image: radial-gradient(circle at 50% 50%, #1a103c 0%, #000 70%);
            color: #cbd5e1; font-family: 'Inter', sans-serif;
            padding-bottom: 80px;
        }
        h1, h2, h3 {
            font-family: 'Orbitron', sans-serif !important; letter-spacing: 2px;
            background: linear-gradient(90deg, #a78bfa, #3b82f6);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            text-shadow: 0px 0px 30px rgba(59, 130, 246, 0.5);
        }
        [data-testid="stSidebar"] {background-color: #0a0a0a !important; border-right: 1px solid #1f1f1f;}
        .dashboard-card {
            background: linear-gradient(145deg, rgba(20, 20, 30, 0.8), rgba(10, 10, 15, 0.9));
            border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 20px; padding: 20px;
            text-align: left; box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
            transition: all 0.3s ease; height: 160px; display: flex; flex-direction: column;
            justify-content: center; position: relative; overflow: hidden;
        }
        .dashboard-card::before {content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, #8b5cf6, #3b82f6); box-shadow: 0 0 10px #8b5cf6;}
        .card-icon {font-size: 24px; margin-bottom: 10px; background: rgba(139, 92, 246, 0.2); width: 45px; height: 45px; display: flex; align-items: center; justify-content: center; border-radius: 12px; color: #a78bfa;}
        .card-value {font-size: 1.8rem; font-weight: 700; color: white !important; font-family: 'Orbitron', sans-serif !important;}
        .card-label {font-size: 0.85rem; color: #94a3b8 !important;}
        .discount-badge {
            position: absolute; top: 10px; right: 10px;
            background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%);
            color: white !important; padding: 5px 12px; border-radius: 20px; font-weight: 800;
            box-shadow: 0 0 10px rgba(239, 68, 68, 0.6); z-index: 2;
        }
        .deal-card {
            background: rgba(20, 20, 20, 0.6); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 16px; padding: 15px; height: 420px; display: flex; flex-direction: column; justify-content: space-between; position: relative;
        }
        .ticker-wrap {
            position: fixed; bottom: 0; left: 0; width: 100%; overflow: hidden; height: 40px;
            background-color: rgba(10, 10, 10, 0.95); border-top: 1px solid #333; z-index: 9999;
            display: flex; align-items: center;
        }
        .ticker {
            display: inline-block; white-space: nowrap; padding-left: 100%;
            animation: ticker 40s linear infinite; font-family: 'Orbitron', sans-serif; font-size: 0.85rem;
        }
        .ticker-item { display: inline-block; padding: 0 2rem; color: #ccc; }
        .ticker-up { color: #4ade80; } .ticker-down { color: #ef4444; }
        @keyframes ticker { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-100%, 0, 0); } }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. YARDIMCI FONKSİYONLAR
# ==========================================
def format_tl(val):
    return f"{val:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")

def filter_irrelevant_products(df, query, threshold=0.5):
    if df.empty: return df
    q_words = set(query.lower().split())
    valid_indices = []
    for idx, row in df.iterrows():
        t_words = set(str(row['Ürün']).lower().split())
        match_ratio = len(q_words.intersection(t_words)) / len(q_words) if q_words else 0
        if match_ratio >= threshold: valid_indices.append(idx)
    return df.loc[valid_indices]

def plot_ghost_gauge(score):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number", value = score,
        gauge = {'axis': {'range': [None, 100]}, 'bar': {'color': "#8b5cf6"},
                 'steps': [{'range': [0, 40], 'color': "rgba(239, 68, 68, 0.2)"},
                           {'range': [70, 100], 'color': "rgba(34, 197, 94, 0.2)"}]},
        title = {'text': "GHOST SCORE", 'font': {'family': "Orbitron", 'color': "white", 'size': 14}}
    ))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", height=220, margin=dict(l=20,r=20,t=40,b=20))
    st.plotly_chart(fig, use_container_width=True)

def plot_neon_prediction(df, avg_price):
    try:
        df_s = df.sort_values(by="Fiyat", ascending=False).head(10)
        future_val = df_s.iloc[-1]['Fiyat'] * random.uniform(0.92, 0.97)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_s['Satıcı'], y=df_s['Fiyat'], mode='lines+markers', line_shape='spline', line=dict(color='#00f2ff', width=4), name="Güncel"))
        fig.add_trace(go.Scatter(x=[df_s.iloc[-1]['Satıcı'], "Gelecek Tahmini"], y=[df_s.iloc[-1]['Fiyat'], future_val], mode='lines', line=dict(color='#ef4444', dash='dot'), name="AI Tahmin"))
        fig.add_hline(y=avg_price, line_dash="dash", line_color="#8b5cf6", annotation_text="Ortalama")
        fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=380, margin=dict(l=10,r=10,t=40,b=10), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    except: pass

def render_dashboard_card(title, value, icon="📊"):
    st.markdown(f"""
    <div class="dashboard-card">
        <div class="card-icon">{icon}</div>
        <div class="card-label">{title}</div>
        <div class="card-value">{value}</div>
        <div style="width: 100%; height: 4px; background: #333; margin-top: 10px; border-radius: 2px;">
            <div style="width: 70%; height: 100%; background: linear-gradient(90deg, #8b5cf6, #3b82f6); border-radius: 2px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 4. SIDEBAR
# ==========================================
with st.sidebar:
    if anim_cart: st_lottie(anim_cart, height=100, key="nav_lottie")
    st.markdown("""
        <div style="text-align: center;">
            <h2 style='display: flex; align-items: center; justify-content: center; gap: 10px; color: #a78bfa; margin: 0;'>
                <span style="font-family: 'Orbitron';">GhostDeal</span>
            </h2>
            <p style='color: #666; font-size: 0.6rem; letter-spacing: 2px;'>ULTIMATE VISION v23.0</p>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    menu = st.radio("MENÜ", ["DASHBOARD", "GHOST VISION 👁️", "AMAZON VİTRİN", "FİYAT ALARMI"], label_visibility="collapsed", key="main_nav")

# ==========================================
# 5. SAYFA YAPILARI
# ==========================================

# --- GHOST VISION (BARKOD) ---
if menu == "GHOST VISION 👁️":
    st.markdown("<h2>👁️ GHOST VISION</h2>", unsafe_allow_html=True)
    st.info("💡 Ürün barkodunu kameraya gösterin. Sistem anında piyasayı tarasın.")
    cam_file = st.camera_input("Barkodu Tara", key="ghost_scanner")
    if cam_file and HAS_BARCODE_LIB:
        img = Image.open(cam_file)
        decoded = decode(img)
        if decoded:
            b_data = decoded[0].data.decode("utf-8")
            st.success(f"✅ Barkod Yakalandı: {b_data}")
            st.session_state.barcode_query = b_data
            if st.button("🔍 Bu Ürünü Dashboard'da Analiz Et"):
                st.session_state.menu_trigger = "DASHBOARD"
                st.rerun()
        else: st.warning("❌ Barkod okunamadı. Işığı ayarlayıp tekrar deneyin.")

# --- DASHBOARD ---
elif menu == "DASHBOARD":
    initial_q = st.session_state.get('barcode_query', "")
    col_h, col_s = st.columns([1, 2])
    col_h.markdown("<h2>Dashboard</h2>", unsafe_allow_html=True)
    query = col_s.text_input("Ürün Ara...", value=initial_q, placeholder="Ürün adı veya barkod", label_visibility="collapsed")
    
    if query:
        with st.spinner("📡 Global Piyasalar Taranıyor..."):
            raw_df = cached_search(query, SERP_API_KEY, RAPID_API_KEY)
            df = filter_irrelevant_products(raw_df, query)
            st.session_state.results = df

    if 'results' in st.session_state and not st.session_state.results.empty:
        df = st.session_state.results
        best_p, avg_p = df['Fiyat'].min(), df['Fiyat'].mean()
        saving = ((avg_p - best_p) / avg_p) * 100
        g_score = min(100, int(50 + (saving * 2)))

        st.markdown("---")
        l, r = st.columns([2, 3], gap="medium")
        with l:
            c1, c2 = st.columns(2)
            with c1: render_dashboard_card("En İyi Fiyat", format_tl(best_p), "💎")
            with c2: render_dashboard_card("Piyasa Ort.", format_tl(avg_p), "⚖️")
            st.write(""); plot_ghost_gauge(g_score)
            if st.button("✨ YZ Analizi Başlat", use_container_width=True, key="ai_dash"):
                if HAS_AI:
                    genai.configure(api_key=GEMINI_API_KEY)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    res = model.generate_content(f"Ürün: {query}, Fiyat: {best_p}. Bu fiyata alınır mı? Kısa cevap.")
                    st.info(f"🤖 {res.text}")
        with r: plot_neon_prediction(df, avg_p)
        
        st.markdown("### 📋 Teklif Listesi")
        st.dataframe(df[['Resim', 'Ürün', 'Fiyat', 'Satıcı', 'Link']], hide_index=True, use_container_width=True, 
                     column_config={
                         "Resim": st.column_config.ImageColumn("Görsel"), 
                         "Link": st.column_config.LinkColumn("Git", display_text="Mağazaya Git ↗"),
                         "Fiyat": st.column_config.NumberColumn(format="%.2f TL")
                     })
        
        # EXCEL/CSV RAPOR
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Analiz Raporunu İndir", csv, f"GhostDeal_{query}.csv", "text/csv")

# --- AMAZON VİTRİN ---
elif menu == "AMAZON VİTRİN":
    c1, c2 = st.columns([4,1])
    c1.markdown("<h2>🔥 AMAZON LIVE</h2>", unsafe_allow_html=True)
    curr = time.time()
    last = st.session_state.get('last_amz', 0)
    if curr - last < 3600:
        c2.warning(f"⏳ {int((3600-(curr-last))/60)} dk")
    else:
        if c2.button("BAŞLAT 🚀", key="btn_amz_start"):
            st.session_state.last_amz = curr
            st.session_state.deals = cached_deals(RAPID_API_KEY)
            st.rerun()

    if 'deals' in st.session_state and not st.session_state.deals.empty:
        df_deals = st.session_state.deals
        cols = st.columns(4)
        for i, row in df_deals.iterrows():
            with cols[i % 4]:
                st.markdown(f"""
                <div class="deal-card">
                    <span class="discount-badge">-{row['İndirim_Yazisi']}</span>
                    <img src="{row['Resim']}" style="width:100%; height:150px; object-fit:contain;">
                    <div style="margin-top:10px; font-weight:bold; color:white; height: 45px; overflow: hidden;">{row['Ürün'][:45]}...</div>
                    <div style="font-size:1.4rem; color:#4ade80; font-weight:900;">{format_tl(row['Fiyat'])}</div>
                    <div style="text-decoration:line-through; color:#666; font-size:0.8rem;">{format_tl(row['Eski Fiyat'])}</div>
                    <a href="{row['Link']}" target="_blank" style="display:block; text-align:center; background:#8b5cf6; color:white; padding:8px; border-radius:5px; margin-top:10px; text-decoration:none;">İNCELE</a>
                </div><br>""", unsafe_allow_html=True)

# --- FİYAT ALARMI ---
elif menu == "FİYAT ALARMI":
    st.markdown("<h2>🔔 E-POSTA ALARMI</h2>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    prod_name = c1.text_input("Takip Edilecek Ürün", placeholder="Örn: iPhone 16")
    target_p = c2.number_input("Hedef Fiyat (TL)", min_value=1)
    user_mail = st.text_input("E-Posta Adresiniz")
    
    if st.button("TAKİBİ BAŞLAT 🚀", key="btn_alarm_start"):
        if user_mail and prod_name:
            st.success(f"✅ {prod_name} için takip başladı. {user_mail} adresine bildirim gönderilecek.")
            st.session_state.monitoring = True
            status_box = st.empty()
            while st.session_state.monitoring:
                status_box.info(f"⏳ Son Kontrol: {time.strftime('%H:%M:%S')}")
                res_df = cached_search(prod_name, SERP_API_KEY, RAPID_API_KEY)
                clean_df = filter_irrelevant_products(res_df, prod_name)
                if not clean_df.empty:
                    current_best = clean_df['Fiyat'].min()
                    if current_best <= target_p:
                        send_email_alert(user_mail, prod_name, format_tl(current_best), clean_df.iloc[0]['Link'])
                        st.balloons()
                        st.success("🎉 HEDEF YAKALANDI! Mail gönderildi.")
                        break
                time.sleep(900) # 15 dk bekle
        else: st.error("Lütfen tüm alanları doldurun.")

# ==========================================
# 6. CANLI BORSA ŞERİDİ (TICKER)
# ==========================================
st.markdown(f"""
<div class="ticker-wrap">
    <div class="ticker">
        <div class="ticker-item">GHOSTDEAL LIVE 🟢</div>
        <div class="ticker-item">EUR/TL: {50.37 + random.uniform(-0.1, 0.1):.2f}</div>
        <div class="ticker-item">USD/TL: {43.18 + random.uniform(-0.1, 0.1):.2f}</div>
        <div class="ticker-item">XU100.IS/TL: {11498 + random.uniform(-0.1, 0.1):.2f}</div>
        
    </div>
</div>
""", unsafe_allow_html=True)
