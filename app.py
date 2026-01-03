import streamlit as st
import pandas as pd
import time
import requests
import plotly.graph_objects as go
from streamlit_lottie import st_lottie
from engine import search_all_sources, get_amazon_deals

# ==========================================
# 1. AYARLAR, GÜVENLİK VE LOTTIE LOADER
# ==========================================
st.set_page_config(page_title="GhostDeal Pro", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# --- LOTTIE ANİMASYON YÜKLEYİCİ ---
def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        if r.status_code != 200: return None
        return r.json()
    except: return None

# Animasyonları Hazırla
lottie_tech = load_lottieurl("https://lottie.host/4b90a66a-1234-4567-8910-1234567890ab/placeholder.json") # Yedek link
# Gerçek linkler (Eğer yüklenmezse boş geçer)
anim_search = load_lottieurl("https://assets9.lottiefiles.com/packages/lf20_w51pcehl.json")
anim_cart = load_lottieurl("https://assets10.lottiefiles.com/packages/lf20_6wjmecxo.json")

# --- CACHING (ÖNBELLEK) ---
@st.cache_data(ttl=3600, show_spinner=False)
def cached_search(query, serp_key, rapid_key):
    return search_all_sources(query, serp_key, rapid_key)

@st.cache_data(ttl=3600, show_spinner=False)
def cached_deals(rapid_key, country="TR"):
    return get_amazon_deals(rapid_key, country)

# --- GÜVENLİK DUVARI ---
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

# --- API KEY YÜKLEME ---
try:
    if check_password():
        SERP_API_KEY = st.secrets["SERP_API_KEY"]
        RAPID_API_KEY = st.secrets["RAPID_API_KEY"]
        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    else: st.stop()
except:
    st.warning("⚠️ API Anahtarları bulunamadı. Lütfen Secrets ayarlarını yapın.")
    st.stop()

# --- AI KONTROL ---
try:
    import google.generativeai as genai
    HAS_AI_LIBRARY = True
except: HAS_AI_LIBRARY = False

# ==========================================
# 2. CYBERPUNK CSS TASARIM (AURORA & NEON)
# ==========================================
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Orbitron:wght@500;700;900&display=swap');

        /* --- 1. LIVING BACKGROUND --- */
        .stApp {
            background: linear-gradient(-45deg, #0e1117, #1a103c, #0f172a, #000000);
            background-size: 400% 400%;
            animation: gradientBG 15s ease infinite;
        }
        @keyframes gradientBG {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        /* --- 2. FONTLAR VE RENKLER --- */
        h1, h2, h3 {
            font-family: 'Orbitron', sans-serif !important;
            background: -webkit-linear-gradient(45deg, #fff, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-shadow: 0px 0px 20px rgba(167, 139, 250, 0.3);
        }
        p, div, span, label { font-family: 'Inter', sans-serif !important; color: #e2e8f0 !important; }
        
        /* --- 3. SIDEBAR --- */
        [data-testid="stSidebar"] { background-color: rgba(22, 27, 34, 0.8) !important; backdrop-filter: blur(10px); border-right: 1px solid #30363d; }
        
        /* --- 4. CAM KARTLAR (GLASSMORPHISM) --- */
        .deal-card {
            background: rgba(30, 30, 30, 0.4); 
            backdrop-filter: blur(10px); 
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px; padding: 15px; height: 420px;
            display: flex; flex-direction: column; justify-content: space-between;
            transition: all 0.4s; position: relative; overflow: hidden;
        }
        .deal-card:hover {
            transform: translateY(-10px) scale(1.02);
            border-color: #8b5cf6;
            box-shadow: 0 0 20px rgba(139, 92, 246, 0.4);
        }

        .discount-badge {
            background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%);
            color: white !important; padding: 6px 12px; border-radius: 20px;
            font-size: 0.85rem; font-weight: 800; position: absolute; top: 12px; right: 12px;
        }
        
        .deal-img-container {
            background: #ffffff; border-radius: 12px; padding: 10px; height: 180px;
            display: flex; align-items: center; justify-content: center; margin-bottom: 12px;
        }
        .deal-img { max-height: 100%; max-width: 100%; object-fit: contain; }
        
        .deal-title {
            font-size: 0.95rem; line-height: 1.4; height: 60px;
            overflow: hidden; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
        }

        .price-new {
            font-size: 1.5rem; font-weight: 800;
            background: -webkit-linear-gradient(45deg, #4ade80, #22c55e);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }

        .action-btn {
            background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 100%);
            color: white !important; padding: 10px; border-radius: 8px; text-align: center;
            text-decoration: none; font-weight: 600; margin-top: 12px; display:block;
        }

        /* --- 5. INPUTLAR VE BUTONLAR --- */
        .stTextInput > div > div > input, .stNumberInput > div > div > input {
            background-color: rgba(30, 30, 30, 0.6) !important;
            color: white !important; border: 1px solid #444 !important;
        }
        .stButton > button {
            background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%);
            border: none; color: white !important; font-weight: bold;
        }
        
        /* --- 6. WINNER SECTION --- */
        .winner-section {
            background: linear-gradient(145deg, rgba(30,41,59,0.8), rgba(15,23,42,0.9));
            border: 1px solid #334155; border-radius: 16px; padding: 30px;
            display: flex; align-items: center; justify-content: space-between;
            box-shadow: 0 0 30px rgba(56, 189, 248, 0.1);
        }
        .winner-price {
            font-size: 3.5rem; font-weight: 900; font-family: 'Orbitron', sans-serif;
            background: -webkit-linear-gradient(45deg, #38bdf8, #818cf8);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. YARDIMCI FONKSİYONLAR (KPI, Chart, Telegram)
# ==========================================
def format_tl(val):
    return f"{val:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")

def render_kpi_card(title, value, icon="💰", color="#8b5cf6"):
    st.markdown(f"""
    <div style="background: rgba(255,255,255,0.05); border: 1px solid {color}; border-radius: 12px; padding: 15px; text-align: center; box-shadow: 0 0 15px {color}30;">
        <div style="font-size: 1.8rem;">{icon}</div>
        <div style="color: #94a3b8; font-size: 0.8rem; margin-top: 5px;">{title}</div>
        <div style="color: white; font-size: 1.3rem; font-weight: bold; margin-top: 5px;">{value}</div>
    </div>
    """, unsafe_allow_html=True)

def plot_neon_chart(df):
    try:
        top5 = df.head(5)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=top5['Satıcı'], y=top5['Fiyat'],
            mode='lines+markers',
            line=dict(color='#8b5cf6', width=4),
            marker=dict(size=12, color='#fff', line=dict(width=2, color='#8b5cf6')),
            fill='tozeroy', fillcolor='rgba(139, 92, 246, 0.1)'
        ))
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'), height=300, margin=dict(l=20, r=20, t=30, b=20),
            xaxis=dict(showgrid=False), yaxis=dict(gridcolor='#333')
        )
        st.plotly_chart(fig, use_container_width=True)
    except: pass

def send_telegram_msg(token, chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})
        return True
    except: return False

def get_seasonal_advice(product_name, current_price):
    if not HAS_AI_LIBRARY or not GEMINI_API_KEY: return None
    genai.configure(api_key=GEMINI_API_KEY)
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"Rol: Analist. Ürün: {product_name}, Fiyat: {current_price}. AL/BEKLE/SAT tavsiyesi ver. Kısa Türkçe."
        return model.generate_content(prompt).text
    except: return None

# ==========================================
# 4. SIDEBAR & NAVİGASYON
# ==========================================
with st.sidebar:
    if anim_cart: st_lottie(anim_cart, height=120, key="cart_anim")
    
    st.markdown("""
        <div style="text-align: center; padding: 10px 0;">
            <h2 style="color:white; margin:0;">GhostDeal</h2>
            <p style="color:#64748b; font-size: 0.7rem; letter-spacing: 2px;">ULTIMATE v16.0</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    menu = st.radio("MENÜ", ["🔎 Analiz & Arama", "🔥 Günün Fırsatları", "🔔 Fiyat Alarmı"], label_visibility="collapsed")
    st.markdown("---")
    st.success("🟢 System Online")

# ==========================================
# 5. SAYFA İÇERİKLERİ
# ==========================================

# --- A: ARAMA ---
if menu == "🔎 Analiz & Arama":
    st.markdown("<h2>🔎 PİYASA ANALİZİ</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([5, 1])
    with col1: query = st.text_input("Ürün Ara", placeholder="Örn: iPhone 15 Pro Max...", label_visibility="collapsed")
    with col2: search_btn = st.button("ANALİZ ET", use_container_width=True)

    if search_btn and query:
        with st.status("📡 UYDU BAĞLANTISI KURULUYOR...", expanded=True) as status:
            st.write("🔍 Global veritabanları taranıyor...")
            time.sleep(0.5)
            st.write("🧩 Çöp veriler temizleniyor...")
            df = cached_search(query, SERP_API_KEY, RAPID_API_KEY)
            status.update(label="🚀 GÖREV TAMAMLANDI", state="complete", expanded=False)
            st.session_state.search_results = df
            st.session_state.last_query = query
    
    if 'search_results' in st.session_state and not st.session_state.search_results.empty:
        df = st.session_state.search_results
        best = df.iloc[0]
        avg_price = df['Fiyat'].mean()
        
        # --- KPI DASHBOARD ---
        c1, c2, c3 = st.columns(3)
        with c1: render_kpi_card("En İyi Fiyat", format_tl(best['Fiyat']), "🔥", "#ef4444")
        with c2: render_kpi_card("Ortalama Piyasa", format_tl(avg_price), "⚖️", "#3b82f6")
        with c3: render_kpi_card("Analiz Edilen", f"{len(df)} Mağaza", "🏪", "#22c55e")
        
        st.write("")
        
        # --- WINNER & CHART ---
        wc1, wc2 = st.columns([1, 1])
        with wc1:
            st.markdown(f"""
            <div class="winner-section">
                <div>
                    <span style="color:#94a3b8; font-size:0.9rem;">KAZANAN</span>
                    <div class="winner-price">{format_tl(best['Fiyat'])}</div>
                    <div style="color:#cbd5e1; margin-top:5px;">{best['Ürün']}</div>
                </div>
                <div style="text-align:right;">
                    <span style="background:#0f172a; border:1px solid #334155; padding:5px 15px; border-radius:20px; color:#38bdf8;">{best['Satıcı']}</span>
                    <a href="{best['Link']}" target="_blank" class="action-btn">ÜRÜNE GİT ↗</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # AI Advice
            if st.button("✨ Yapay Zeka Yorumu"):
                 advice = get_seasonal_advice(st.session_state.last_query, format_tl(best['Fiyat']))
                 if advice: st.info(f"🤖 {advice}")
                 
        with wc2:
            st.markdown("#### 📈 Fiyat Dağılımı")
            plot_neon_chart(df)
            
        st.dataframe(df[['Resim', 'Fiyat', 'Satıcı', 'Kaynak', 'Ürün', 'Link']], hide_index=True, use_container_width=True, 
                     column_config={"Fiyat": st.column_config.NumberColumn(format="%.2f TL"), "Link": st.column_config.LinkColumn(display_text="Git"), "Resim": st.column_config.ImageColumn(width="small")})

# --- B: VİTRİN ---
elif menu == "🔥 Günün Fırsatları":
    c_head, c_btn = st.columns([4,1])
    c_head.markdown("<h2>🔥 AMAZON VİTRİNİ</h2>", unsafe_allow_html=True)
    if c_btn.button("YENİLE ↻"):
        with st.spinner("Veriler güncelleniyor..."):
            st.session_state.deals_results = cached_deals(RAPID_API_KEY)
            
    if 'deals_results' in st.session_state and not st.session_state.deals_results.empty:
        df = st.session_state.deals_results
        num_cols = 4
        for i in range(0, len(df), num_cols):
            cols = st.columns(num_cols)
            for j, (_, row) in enumerate(df.iloc[i:i+num_cols].iterrows()):
                with cols[j]:
                    st.markdown(f"""
                    <div class="deal-card">
                        <span class="discount-badge">-{row['İndirim_Yazisi']}</span>
                        <div class="deal-img-container"><img src="{row['Resim']}" class="deal-img"></div>
                        <div class="deal-title" title="{row['Ürün']}">{row['Ürün']}</div>
                        <div class="price-new">{format_tl(row['Fiyat'])}</div>
                        <div style="text-decoration:line-through; color:#666; font-size:0.8rem;">{format_tl(row['Eski Fiyat'])}</div>
                        <a href="{row['Link']}" target="_blank" class="action-btn">İNCELE</a>
                    </div>
                    """, unsafe_allow_html=True)

# --- C: ALARM ---
elif menu == "🔔 Fiyat Alarmı":
    st.markdown("<h2>🔔 FİYAT TAKİPÇİSİ</h2>", unsafe_allow_html=True)
    st.info("Bu sayfa açık kaldığı sürece tarama yapar.")
    
    with st.container():
        c1, c2 = st.columns(2)
        target_product = c1.text_input("Ürün Adı", placeholder="PlayStation 5")
        target_price = c2.number_input("Hedef Fiyat (TL)", min_value=0, value=20000)
        interval = st.slider("Sıklık (Dk)", 5, 60, 15)
        
        with st.expander("Ayarlar"):
            tg_token = st.text_input("Bot Token", type="password")
            tg_chat_id = st.text_input("Chat ID")
            
        if st.button("BAŞLAT"):
            st.session_state.monitoring = True
            status = st.empty()
            send_telegram_msg(tg_token, tg_chat_id, f"✅ Başladı: {target_product}")
            while st.session_state.monitoring:
                status.info(f"⏳ Kontrol: {time.strftime('%H:%M:%S')}")
                df = cached_search(target_product, SERP_API_KEY, RAPID_API_KEY)
                if not df.empty and df.iloc[0]['Fiyat'] <= target_price:
                    send_telegram_msg(tg_token, tg_chat_id, f"🚨 DÜŞTÜ: {df.iloc[0]['Fiyat']} TL")
                    st.balloons()
                    break
                time.sleep(interval * 60)
