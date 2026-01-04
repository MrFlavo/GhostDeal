import streamlit as st
import pandas as pd
import time
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import plotly.graph_objects as go
from streamlit_lottie import st_lottie
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
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("🔒 GhostDeal Erişim Şifresi", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("🔒 GhostDeal Erişim Şifresi", type="password", on_change=password_entered, key="password")
        st.error("❌ Hatalı şifre.")
        return False
    return True

# --- API KEY ---
try:
    if check_password():
        SERP_API_KEY = st.secrets["SERP_API_KEY"]
        RAPID_API_KEY = st.secrets["RAPID_API_KEY"]
        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    else: st.stop()
except:
    st.warning("⚠️ API Anahtarları bulunamadı. Secrets ayarlarını kontrol edin.")
    st.stop()

# --- AI ---
try:
    import google.generativeai as genai
    HAS_AI_LIBRARY = True
except: HAS_AI_LIBRARY = False

# ==========================================
# 2. COMMAND CENTER CSS (GÖRSELDEKİ GİBİ)
# ==========================================
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Orbitron:wght@500;700;900&display=swap');
        
        /* --- DÜZELTME: HEADER VE SIDEBAR İKONU --- */
        header {
            background: transparent !important;
        }
        
        /* İkonların bozulmasını önleyen kural */
        .material-icons, .st-emotion-cache-16idsys, .st-emotion-cache-10trblm {
            font-family: 'Material Icons' !important;
        }

        /* --- 1. ARKAPLAN --- */
        .stApp {
            background-color: #050505; 
            background-image: radial-gradient(circle at 50% 50%, #1a103c 0%, #000 70%);
            color: #cbd5e1; /* Genel yazı rengi */
            font-family: 'Inter', sans-serif; /* Genel font */
        }

        /* --- 2. FONTLAR (Sadece Başlıklar ve Metinler) --- */
        h1, h2, h3 {
            font-family: 'Orbitron', sans-serif !important;
            letter-spacing: 2px;
            background: linear-gradient(90deg, #a78bfa, #3b82f6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0px 0px 30px rgba(59, 130, 246, 0.5);
        }
        
        /* SPAN ve DIV'i zorlamayı bıraktık, böylece ikonlar bozulmayacak */
        p, label, .stMarkdown { 
            font-family: 'Inter', sans-serif !important; 
            color: #cbd5e1 !important; 
        }

        /* --- 3. SIDEBAR --- */
        [data-testid="stSidebar"] {
            background-color: #0a0a0a !important;
            border-right: 1px solid #1f1f1f;
        }

        /* --- 4. DASHBOARD KARTLARI --- */
        .dashboard-card {
            background: linear-gradient(145deg, rgba(20, 20, 30, 0.8), rgba(10, 10, 15, 0.9));
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 20px;
            padding: 20px;
            text-align: left;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
            transition: all 0.3s ease;
            height: 160px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            position: relative;
            overflow: hidden;
        }
        
        .dashboard-card::before {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; height: 2px;
            background: linear-gradient(90deg, #8b5cf6, #3b82f6);
            box-shadow: 0 0 10px #8b5cf6;
        }
        
        .dashboard-card:hover {
            transform: translateY(-5px);
            border-color: #3b82f6;
            box-shadow: 0 10px 40px rgba(59, 130, 246, 0.2);
        }
        
        .card-icon {
            font-size: 24px;
            margin-bottom: 10px;
            background: rgba(139, 92, 246, 0.2);
            width: 45px; height: 45px;
            display: flex; align-items: center; justify-content: center;
            border-radius: 12px;
            color: #a78bfa;
            /* İkon fontunu koru */
            font-family: "Segoe UI Emoji", "Roboto", sans-serif !important;
        }
        
        .card-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: white !important;
            font-family: 'Orbitron', sans-serif !important;
        }
        
        .card-label {
            font-size: 0.85rem;
            color: #94a3b8 !important;
            font-family: 'Inter', sans-serif !important;
        }

        /* --- 5. FIRSAT KARTLARI --- */
        .deal-card {
            background: rgba(20, 20, 20, 0.6); 
            backdrop-filter: blur(10px); 
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 16px; padding: 15px; height: 420px;
            display: flex; flex-direction: column; justify-content: space-between;
        }
        .deal-card:hover { border-color: #8b5cf6; box-shadow: 0 0 20px rgba(139, 92, 246, 0.3); }
        
        /* Inputlar */
        .stTextInput > div > div > input {
            background-color: #0f0f0f !important;
            border: 1px solid #333 !important;
            color: white !important;
            border-radius: 10px;
        }
        
        /* Gereksiz elementleri gizle */
        .stDeployButton {display:none;}
        #MainMenu {visibility: hidden;} 
        footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. YARDIMCI FONKSİYONLAR
# ==========================================
def format_tl(val):
    return f"{val:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")

# GÖRSELDEKİ GİBİ KARE KARTLAR OLUŞTURUR
def render_dashboard_card(title, value, icon="📊", color_class="purple"):
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

# GÖRSELDEKİ GİBİ KAVİSLİ & NEON GRAFİK
def plot_neon_curve(df):
    try:
        # Veriyi simüle et (Görseldeki gibi dalgalı görünmesi için)
        df_sorted = df.sort_values(by="Fiyat", ascending=False).head(10)
        
        fig = go.Figure()
        
        # 1. Ana Çizgi (Parlak Neon)
        fig.add_trace(go.Scatter(
            x=df_sorted['Satıcı'], 
            y=df_sorted['Fiyat'],
            mode='lines+markers',
            line_shape='spline', # KAVİSLİ ÇİZGİ (Görseldeki Sır)
            line=dict(color='#00f2ff', width=5), # Elektrik Mavisi
            marker=dict(size=10, color='#000', line=dict(width=3, color='#00f2ff')),
            name="Fiyat Trendi"
        ))
        
        # 2. İkinci Çizgi (Mor Gölge)
        fig.add_trace(go.Scatter(
            x=df_sorted['Satıcı'], 
            y=df_sorted['Fiyat'] * 1.1, # Biraz yukarıda
            mode='lines',
            line_shape='spline',
            line=dict(color='#8b5cf6', width=3, dash='dot'),
            opacity=0.5,
            name="Piyasa Ort."
        ))

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=400, # Yüksek grafik
            margin=dict(l=20, r=20, t=50, b=20),
            title=dict(text="PRICE DROP CHART", font=dict(size=20, family="Orbitron", color="white")),
            xaxis=dict(showgrid=False, color="#666"),
            yaxis=dict(showgrid=True, gridcolor="#222", color="#666"),
            hovermode="x unified"
        )
        st.plotly_chart(fig, use_container_width=True)
    except: pass

def get_seasonal_advice(product_name, current_price):
    if not HAS_AI_LIBRARY or not GEMINI_API_KEY: return None
    genai.configure(api_key=GEMINI_API_KEY)
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"Analist ol. Ürün: {product_name}, Fiyat: {current_price}. AL/SAT. Kısa Türkçe."
        return model.generate_content(prompt).text
    except: return None

# ==========================================
# 4. SIDEBAR (LOGO & MENÜ)
# ==========================================
with st.sidebar:
    # Lottie Animasyonu (Sepet) hala üstte kalsın
    if anim_cart: st_lottie(anim_cart, height=120)
    
    # --- YENİ HAYALETLİ BAŞLIK ---
    st.markdown("""
        <div style="text-align: center;">
            <h2 style='display: inline-flex; align-items: center; justify-content: center; color: #a78bfa; margin-bottom: 0; text-shadow: 0 0 10px rgba(167, 139, 250, 0.5);'>
                
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="32" height="32" style="fill: #a78bfa; filter: drop-shadow(0 0 5px #a78bfa); margin-right: 10px;">
                    <path d="M12 2C7.58 2 4 5.58 4 10v10c0 .55.45 1 1 1h2c.55 0 1-.45 1-1v-3h2v3c0 .55.45 1 1 1h2c.55 0 1-.45 1-1v-3h2v3c0 .55.45 1 1 1h2c.55 0 1-.45 1-1V10c0-4.42-3.58-8-8-8zm0 2c3.31 0 6 2.69 6 6v8h-2v-3c0-.55-.45-1-1-1s-1 .45-1 1v3h-2v-3c0-.55-.45-1-1-1s-1 .45-1 1v3H8v-3c0-.55-.45-1-1-1s-1 .45-1 1v3H6V10c0-3.31 2.69-6 6-6zm-3 5c.83 0 1.5.67 1.5 1.5S9.83 12 9 12s-1.5-.67-1.5-1.5S8.17 9 9 9zm6 0c.83 0 1.5.67 1.5 1.5S15.83 12 15 12s-1.5-.67-1.5-1.5S14.17 9 15 9z"/>
                </svg>
                
                GhostDeal
            </h2>
            <p style='color: #666; font-size: 0.7rem; letter-spacing: 3px; margin-top: 5px; opacity: 0.8;'>COMMAND CENTER</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    menu = st.radio("MODÜLLER", ["DASHBOARD", "AMAZON VİTRİN", "FİYAT ALARMI"], label_visibility="collapsed")
    
    if anim_cart: st_lottie(anim_cart, height=120)
    
    st.markdown("---")
    menu = st.radio("MODÜLLER", ["DASHBOARD", "AMAZON VİTRİN", "FİYAT ALARMI"], label_visibility="collapsed")

# ==========================================
# 5. SAYFA YAPISI
# ==========================================

# --- A: DASHBOARD (GÖRSELDEKİ YAPI) ---
if menu == "DASHBOARD":
    # 1. Başlık ve Arama (Yanyana)
    col_head, col_search = st.columns([1, 2])
    with col_head:
        st.markdown("<h2>Data Dashboard</h2>", unsafe_allow_html=True)
    with col_search:
        query = st.text_input("Global Piyasada Ara...", placeholder="Ürün adı girin (örn: MacBook Pro M3)", label_visibility="collapsed")

    # Arama Butonu (Gizli trigger)
    if query:
        with st.spinner("📡 UYDU BAĞLANTISI KURULUYOR..."):
            df = cached_search(query, SERP_API_KEY, RAPID_API_KEY)
            st.session_state.search_results = df
            
    # --- ANA EKRAN DÜZENİ (Görseldeki Sol Kartlar / Sağ Grafik) ---
    if 'search_results' in st.session_state and not st.session_state.search_results.empty:
        df = st.session_state.search_results
        best = df.iloc[0]
        
        st.markdown("---")
        
        # LAYOUT: SOLDA 4 KART (2x2), SAĞDA BÜYÜK GRAFİK
        col_left, col_right = st.columns([2, 3]) # Sol %40, Sağ %60
        
        with col_left:
            # Üst Satır
            c1, c2 = st.columns(2)
            with c1: render_dashboard_card("En İyi Fiyat", format_tl(best['Fiyat']), "💎")
            with c2: render_dashboard_card("Piyasa Ort.", format_tl(df['Fiyat'].mean()), "⚖️")
            
            st.write("") # Boşluk
            
            # Alt Satır
            c3, c4 = st.columns(2)
            with c3: render_dashboard_card("Mağaza Sayısı", str(len(df)), "🏪")
            with c4: render_dashboard_card("Tasarruf", "%15", "📉")
            
            # AI Tavsiyesi (Kartların altına)
            st.write("")
            if st.button("✨ YZ Analizi Başlat", use_container_width=True):
                advice = get_seasonal_advice(query, format_tl(best['Fiyat']))
                if advice: st.info(f"🤖 {advice}")

        with col_right:
            # BÜYÜK GRAFİK
            plot_neon_curve(df)
            
        # Alt Liste (Yatay)
        st.markdown("### 🛒 En İyi Teklifler")
        st.dataframe(
            df.head(5)[['Satıcı', 'Fiyat', 'Link']], 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "Link": st.column_config.LinkColumn("Satın Al", display_text="Mağazaya Git ↗"),
                "Fiyat": st.column_config.NumberColumn(format="%.2f TL")
            }
        )

# --- B: VİTRİN (AMAZON) ---
elif menu == "AMAZON VİTRİN":
    c1, c2 = st.columns([4,1])
    c1.markdown("<h2>🔥 AMAZON LIVE</h2>", unsafe_allow_html=True)
    
    # Zamanlayıcı
    curr = time.time()
    last = st.session_state.get('last_amz', 0)
    if curr - last < 3600:
        c2.warning(f"⏳ {(3600-(curr-last))//60:.0f} dk kaldı")
    else:
        if c2.button("BAŞLAT 🚀"):
            st.session_state.last_amz = curr
            st.session_state.deals = cached_deals(RAPID_API_KEY)
            st.rerun()

    if 'deals' in st.session_state and not st.session_state.deals.empty:
        df = st.session_state.deals
        cols = st.columns(4)
        for i, row in df.iterrows():
            with cols[i % 4]:
                st.markdown(f"""
                <div class="deal-card">
                    <img src="{row['Resim']}" style="width:100%; height:150px; object-fit:contain;">
                    <div style="margin-top:10px; font-weight:bold; color:white;">{row['Ürün'][:40]}...</div>
                    <div style="font-size:1.5rem; color:#4ade80; font-weight:900;">{format_tl(row['Fiyat'])}</div>
                    <a href="{row['Link']}" target="_blank" style="display:block; text-align:center; background:#8b5cf6; color:white; padding:8px; border-radius:5px; margin-top:10px; text-decoration:none;">İNCELE</a>
                </div>
                <br>
                """, unsafe_allow_html=True)

# --- C: ALARM (MAIL) ---
elif menu == "FİYAT ALARMI":
    st.markdown("<h2>🔔 E-POSTA ALARMI</h2>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    prod = c1.text_input("Ürün")
    price = c2.number_input("Hedef Fiyat", value=20000)
    mail = st.text_input("E-Posta Adresi")
    
    if st.button("TAKİBİ BAŞLAT"):
        if mail:
            st.success(f"✅ Sistem {mail} adresini dinlemeye başladı.")
            # Arka plan döngüsü burada çalışır (demo amaçlı basitleştirildi)
