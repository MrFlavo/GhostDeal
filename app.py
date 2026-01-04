import streamlit as st
import pandas as pd
import time
import requests
import smtplib
import difflib # YENİ KÜTÜPHANE: Kelime benzerliği için
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

# --- MAİL GÖNDERME ---
def send_email_alert(to_email, product_name, price, link):
    try:
        sender_email = st.secrets["EMAIL_SENDER"]
        sender_password = st.secrets["EMAIL_PASSWORD"]
        
        subject = f"🚨 FİYAT DÜŞTÜ: {product_name}"
        body = f"""
        <html><body>
            <h2>🔥 GhostDeal Yakaladı!</h2>
            <h3>📦 {product_name}</h3>
            <h1 style="color:green;">{price}</h1>
            <a href="{link}">ÜRÜNE GİT</a>
        </body></html>
        """
        msg = MIMEMultipart()
        msg['From'] = "GhostDeal AI <" + sender_email + ">"
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
        .material-icons, .st-emotion-cache-16idsys {font-family: 'Material Icons' !important;}

        .stApp {
            background-color: #050505; 
            background-image: radial-gradient(circle at 50% 50%, #1a103c 0%, #000 70%);
            color: #cbd5e1; font-family: 'Inter', sans-serif;
        }

        h1, h2, h3 {
            font-family: 'Orbitron', sans-serif !important; letter-spacing: 2px;
            background: linear-gradient(90deg, #a78bfa, #3b82f6);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            text-shadow: 0px 0px 30px rgba(59, 130, 246, 0.5);
        }
        p, label, .stMarkdown {font-family: 'Inter', sans-serif !important; color: #cbd5e1 !important;}

        [data-testid="stSidebar"] {background-color: #0a0a0a !important; border-right: 1px solid #1f1f1f;}

        .dashboard-card {
            background: linear-gradient(145deg, rgba(20, 20, 30, 0.8), rgba(10, 10, 15, 0.9));
            border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 20px; padding: 20px;
            text-align: left; box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
            transition: all 0.3s ease; height: 160px; display: flex; flex-direction: column;
            justify-content: center; position: relative; overflow: hidden;
        }
        .dashboard-card:hover {transform: translateY(-5px); border-color: #3b82f6; box-shadow: 0 10px 40px rgba(59, 130, 246, 0.2);}
        .dashboard-card::before {content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: linear-gradient(90deg, #8b5cf6, #3b82f6); box-shadow: 0 0 10px #8b5cf6;}
        
        .card-icon {font-size: 24px; margin-bottom: 10px; background: rgba(139, 92, 246, 0.2); width: 45px; height: 45px; display: flex; align-items: center; justify-content: center; border-radius: 12px; color: #a78bfa; font-family: sans-serif !important;}
        .card-value {font-size: 1.8rem; font-weight: 700; color: white !important; font-family: 'Orbitron', sans-serif !important;}
        .card-label {font-size: 0.85rem; color: #94a3b8 !important; font-family: 'Inter', sans-serif !important;}

        .discount-badge {
            position: absolute; top: 10px; right: 10px;
            background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%);
            color: white !important; padding: 5px 12px; border-radius: 20px;
            font-size: 0.8rem; font-weight: 800; box-shadow: 0 0 10px rgba(239, 68, 68, 0.6); z-index: 2;
        }
        .deal-card {
            background: rgba(20, 20, 20, 0.6); backdrop-filter: blur(10px); 
            border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 16px; padding: 15px; height: 420px;
            display: flex; flex-direction: column; justify-content: space-between;
        }
        .deal-card:hover { border-color: #8b5cf6; box-shadow: 0 0 20px rgba(139, 92, 246, 0.3); }
        
        .stTextInput > div > div > input {background-color: #0f0f0f !important; border: 1px solid #333 !important; color: white !important; border-radius: 10px;}
        .stDeployButton, #MainMenu, footer {display:none; visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. YARDIMCI FONKSİYONLAR
# ==========================================
def format_tl(val):
    return f"{val:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")

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

# --- YENİ: AKILLI FİLTRELEME MOTORU ---
def filter_irrelevant_products(df, query, threshold=0.4):
    """
    Sorgudaki kelimelerin ürün başlığında geçme oranına göre filtreler.
    threshold=0.4 demek, arattığın kelimelerin en az %40'ı üründe geçmeli.
    """
    if df.empty: return df
    
    # Sorguyu kelimelerine ayır ve küçült
    query_words = set(query.lower().split())
    
    valid_indices = []
    
    for index, row in df.iterrows():
        title_words = set(str(row['Ürün']).lower().split())
        # Kesişim kümesi (Ortak kelimeler)
        common_words = query_words.intersection(title_words)
        
        # Eşleşme oranı
        if len(query_words) > 0:
            match_ratio = len(common_words) / len(query_words)
        else:
            match_ratio = 0
            
        # Eğer eşleşme oranı eşikten büyükse listeye al
        if match_ratio >= threshold:
            valid_indices.append(index)
            
    return df.loc[valid_indices]

def plot_neon_curve(df, avg_price, best_price):
    try:
        df_sorted = df.sort_values(by="Fiyat", ascending=False).head(15)
        fig = go.Figure()
        # Ana Çizgi
        fig.add_trace(go.Scatter(
            x=df_sorted['Satıcı'], y=df_sorted['Fiyat'], mode='lines+markers', line_shape='spline',
            line=dict(color='#00f2ff', width=4), marker=dict(size=8, color='#000', line=dict(width=2, color='#00f2ff')),
            name="Mağaza Fiyatı"
        ))
        # Ortalama Çizgisi
        fig.add_hline(y=avg_price, line_dash="dash", line_color="#8b5cf6", annotation_text="Ortalama")
        # En İyi Fiyat Alanı
        fig.add_hrect(y0=0, y1=best_price * 1.05, fillcolor="green", opacity=0.1, line_width=0)
        
        fig.update_layout(
            template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            height=380, margin=dict(l=20, r=20, t=40, b=20),
            title=dict(text="FİYAT ANALİZİ", font=dict(family="Orbitron", color="white")),
            xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showgrid=True, gridcolor="#222")
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
# 4. SIDEBAR
# ==========================================
with st.sidebar:
    if anim_cart: st_lottie(anim_cart, height=120, key="lottie_cart_sidebar")
    
    st.markdown("""
        <div style="text-align: center;">
            <h2 style='display: flex; align-items: center; justify-content: center; gap: 10px; color: #a78bfa; margin: 0; padding: 0; text-shadow: 0 0 10px rgba(167, 139, 250, 0.5);'>
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="32" height="32" style="fill: #a78bfa; filter: drop-shadow(0 0 5px #a78bfa);">
                    <path d="M12 2C7.58 2 4 5.58 4 10v10c0 .55.45 1 1 1h2c.55 0 1-.45 1-1v-3h2v3c0 .55.45 1 1 1h2c.55 0 1-.45 1-1v-3h2v3c0 .55.45 1 1 1h2c.55 0 1-.45 1-1v-3h2v3c0 .55.45 1 1 1h2c.55 0 1-.45 1-1V10c0-4.42-3.58-8-8-8zm0 2c3.31 0 6 2.69 6 6v8h-2v-3c0-.55-.45-1-1-1s-1 .45-1 1v3h-2v-3c0-.55-.45-1-1-1s-1 .45-1 1v3H8v-3c0-.55-.45-1-1-1s-1 .45-1 1v3H6V10c0-3.31 2.69-6 6-6zm-3 5c.83 0 1.5.67 1.5 1.5S9.83 12 9 12s-1.5-.67-1.5-1.5S8.17 9 9 9zm6 0c.83 0 1.5.67 1.5 1.5S15.83 12 15 12s-1.5-.67-1.5-1.5S14.17 9 15 9z"/>
                </svg>
                <span style="font-family: 'Orbitron', sans-serif;">GhostDeal</span>
            </h2>
            <p style='color: #666; font-size: 0.7rem; letter-spacing: 3px; margin-top: 5px; opacity: 0.8; font-family: "Inter", sans-serif;'>COMMAND CENTER</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    menu = st.radio("MODÜLLER", ["DASHBOARD", "AMAZON VİTRİN", "FİYAT ALARMI"], label_visibility="collapsed", key="main_nav_final")

# ==========================================
# 5. SAYFA YAPISI
# ==========================================

# --- A: DASHBOARD ---
if menu == "DASHBOARD":
    col_head, col_search = st.columns([1, 2])
    with col_head: st.markdown("<h2>Data Dashboard</h2>", unsafe_allow_html=True)
    with col_search: query = st.text_input("Global Piyasada Ara...", placeholder="Örn: Stanley IceFlow 0.47", label_visibility="collapsed")

    if query:
        with st.spinner("📡 Veriler Toplanıyor ve Temizleniyor..."):
            raw_df = cached_search(query, SERP_API_KEY, RAPID_API_KEY)
            
            # --- YENİ: FİLTRELEME ADIMI ---
            # %50 kelime eşleşmesi olmayan ürünleri çöpe at
            df = filter_irrelevant_products(raw_df, query, threshold=0.5) 
            
            st.session_state.search_results = df
            
    if 'search_results' in st.session_state and not st.session_state.search_results.empty:
        df = st.session_state.search_results
        
        # İstatistikler (Filtrelenmiş veriden)
        best_price = df['Fiyat'].min()
        avg_price = df['Fiyat'].mean()
        max_price = df['Fiyat'].max()
        saving_ratio = ((avg_price - best_price) / avg_price) * 100
        
        st.markdown("---")
        col_left, col_right = st.columns([2, 3], gap="medium")
        
        with col_left:
            c1, c2 = st.columns(2)
            with c1: render_dashboard_card("En İyi Fiyat", format_tl(best_price), "💎")
            with c2: render_dashboard_card("Piyasa Ort.", format_tl(avg_price), "⚖️")
            st.write("")
            c3, c4 = st.columns(2)
            with c3: render_dashboard_card("Fiyat Farkı", f"%{saving_ratio:.1f}", "📉")
            with c4: render_dashboard_card("Mağaza", str(len(df)), "🏪")
            st.write("")
            if st.button("✨ YZ Analizi Başlat", use_container_width=True, key="ai_btn"):
                advice = get_seasonal_advice(query, format_tl(best_price))
                if advice: st.info(f"🤖 {advice}")

        with col_right:
            plot_neon_curve(df, avg_price, best_price)
            
        st.markdown(f"### 🛒 Filtrelenmiş Sonuçlar: {query}")
        st.dataframe(
            df.sort_values(by="Fiyat")[['Resim', 'Ürün', 'Fiyat', 'Satıcı', 'Link']], 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "Resim": st.column_config.ImageColumn("Görsel", width="small"),
                "Ürün": st.column_config.TextColumn("Ürün Adı", width="large"),
                "Link": st.column_config.LinkColumn("Satın Al", display_text="Mağazaya Git ↗"),
                "Fiyat": st.column_config.ProgressColumn("Fiyat", format="%.2f TL", min_value=best_price, max_value=max_price)
            }
        )
    elif 'search_results' in st.session_state:
        st.warning("⚠️ Aradığınız kriterlere uygun ürün bulunamadı. Lütfen ürün adını daha genel yazın.")

# --- B: VİTRİN ---
elif menu == "AMAZON VİTRİN":
    c1, c2 = st.columns([4,1])
    c1.markdown("<h2>🔥 AMAZON LIVE</h2>", unsafe_allow_html=True)
    
    curr = time.time()
    last = st.session_state.get('last_amz', 0)
    
    if curr - last < 3600:
        remaining = int((3600 - (curr - last)) / 60)
        c2.warning(f"⏳ {remaining} dk kaldı")
    else:
        if c2.button("BAŞLAT 🚀", key="btn_amazon_start"):
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
                    <span class="discount-badge">-{row['İndirim_Yazisi']}</span>
                    <img src="{row['Resim']}" style="width:100%; height:150px; object-fit:contain;">
                    <div style="margin-top:10px; font-weight:bold; color:white; height: 50px; overflow: hidden;">{row['Ürün'][:50]}...</div>
                    <div style="font-size:1.5rem; color:#4ade80; font-weight:900;">{format_tl(row['Fiyat'])}</div>
                    <div style="text-decoration:line-through; color:#666; font-size:0.8rem;">{format_tl(row['Eski Fiyat'])}</div>
                    <a href="{row['Link']}" target="_blank" style="display:block; text-align:center; background:#8b5cf6; color:white; padding:8px; border-radius:5px; margin-top:10px; text-decoration:none;">İNCELE</a>
                </div>
                <br>
                """, unsafe_allow_html=True)

# --- C: ALARM ---
elif menu == "FİYAT ALARMI":
    st.markdown("<h2>🔔 E-POSTA ALARMI</h2>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    prod = c1.text_input("Ürün", placeholder="iPhone 15")
    price = c2.number_input("Hedef Fiyat", value=20000)
    mail = st.text_input("E-Posta Adresi")
    
    if st.button("TAKİBİ BAŞLAT", key="btn_alarm_start"):
        if mail and prod:
            st.success(f"✅ Takip Başladı! {mail} adresine bildirim gidecek.")
            st.session_state.monitoring = True
            status = st.empty()
            while st.session_state.monitoring:
                status.info(f"⏳ Taranıyor: {time.strftime('%H:%M:%S')}")
                # Alarmda da filtreli arama yapıyoruz ki yanlış alarma düşmesin
                raw_df = cached_search(prod, SERP_API_KEY, RAPID_API_KEY)
                df = filter_irrelevant_products(raw_df, prod, threshold=0.5)
                
                if not df.empty:
                    best_row = df.sort_values(by="Fiyat").iloc[0]
                    if best_row['Fiyat'] <= price:
                        send_email_alert(mail, best_row['Ürün'], format_tl(best_row['Fiyat']), best_row['Link'])
                        st.balloons()
                        st.success("HEDEF YAKALANDI! Mail gönderildi.")
                        st.session_state.monitoring = False
                        break
                time.sleep(900)
        else:
            st.error("Lütfen tüm alanları doldurun.")
