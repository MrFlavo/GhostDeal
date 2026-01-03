import streamlit as st
import pandas as pd
import time
import requests
from engine import search_all_sources, get_amazon_deals

# ==========================================
# 1. SAYFA AYARLARI VE GÜVENLİK
# ==========================================
st.set_page_config(page_title="GhostDeal Pro", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# --- GÜVENLİK DUVARI (LOGIN FONKSİYONU) ---
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Şifreyi session'dan sil
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # İlk açılış, henüz şifre girilmedi
        st.text_input(
            "🔒 GhostDeal Erişim Şifresi", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Şifre yanlış
        st.text_input(
            "🔒 GhostDeal Erişim Şifresi", type="password", on_change=password_entered, key="password"
        )
        st.error("❌ Hatalı şifre. Lütfen tekrar deneyin.")
        return False
    else:
        # Şifre doğru
        return True

# --- API ANAHTARLARINI GİZLİ KASADAN ÇEKME ---
# Eğer Streamlit Cloud'da secret ayarlanmadıysa hata vermemesi için kontrol
try:
    if check_password():
        # Sadece şifre doğruysa anahtarları yükle
        SERP_API_KEY = st.secrets["SERP_API_KEY"]
        RAPID_API_KEY = st.secrets["RAPID_API_KEY"]
        GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    else:
        st.stop() # Şifre girilmeden aşağıya inme
except Exception as e:
    st.warning("⚠️ API Anahtarları (Secrets) bulunamadı. Lütfen Streamlit Cloud ayarlarından ekleyin.")
    st.stop()
    
# --- AI KONTROLÜ ---
try:
    import google.generativeai as genai
    HAS_AI_LIBRARY = True
except ImportError:
    HAS_AI_LIBRARY = False

# ==========================================
# 0. ELITE UI TASARIM & CSS (ZORLAMALI DARK MODE)
# ==========================================
st.set_page_config(page_title="GhostDeal Pro", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
        /* --- 1. ANA ARKAPLAN VE YAZI RENGİ (ZORLAMALI) --- */
        .stApp {
            background-color: #0e1117 !important;
        }
        
        /* Tüm metin elementlerini hedef al ve BEYAZ yap */
        p, h1, h2, h3, h4, h5, h6, li, label, .stMarkdown, .stText, span {
            color: #ffffff !important;
        }
        
        /* --- 2. SIDEBAR --- */
        [data-testid="stSidebar"] {
            background-color: #161b22 !important;
            border-right: 1px solid #30363d;
        }
        [data-testid="stSidebar"] * {
            color: #e6edf3 !important;
        }

        /* --- 3. INPUT ALANLARI (ÖNEMLİ: Yazı okunur olsun diye) --- */
        .stTextInput > div > div > input, 
        .stNumberInput > div > div > input {
            background-color: #1e1e1e !important;
            color: #ffffff !important;
            border: 1px solid #444 !important;
        }
        
        /* --- 4. KART TASARIMLARI --- */
        
        /* Fırsat Kartı */
        .deal-card {
            background: #1e1e1e;
            border: 1px solid #333;
            border-radius: 16px;
            padding: 12px;
            height: 420px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }
        .deal-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 10px 30px -10px rgba(139, 92, 246, 0.3);
            border-color: #8b5cf6;
        }

        /* İndirim Rozeti */
        .discount-badge {
            background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%);
            color: white !important;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 800;
            position: absolute;
            top: 12px;
            right: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            z-index: 10;
        }

        /* Resim Alanı */
        .deal-img-container {
            background: #ffffff;
            border-radius: 12px;
            padding: 10px;
            height: 180px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 12px;
        }
        .deal-img {
            max-height: 100%;
            max-width: 100%;
            object-fit: contain;
        }

        /* Başlıklar */
        .deal-title {
            font-size: 0.95rem;
            color: #e2e8f0 !important;
            line-height: 1.4;
            height: 60px;
            overflow: hidden;
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            margin-bottom: 8px;
            opacity: 0.9;
        }
        
        .price-wrapper {
            margin-top: auto;
            text-align: left;
        }
        .price-old {
            text-decoration: line-through;
            color: #64748b !important;
            font-size: 0.9rem;
        }
        .price-new {
            font-size: 1.5rem;
            font-weight: 800;
            background: -webkit-linear-gradient(45deg, #4ade80, #22c55e);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        /* Butonlar */
        .action-btn {
            display: block;
            width: 100%;
            background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 100%);
            color: white !important;
            padding: 10px;
            border-radius: 8px;
            text-align: center;
            text-decoration: none;
            font-weight: 600;
            margin-top: 12px;
            border: none;
            transition: opacity 0.2s;
        }
        .action-btn:hover { opacity: 0.9; }

        /* Winner Section */
        .winner-section {
            background: linear-gradient(145deg, #1e293b, #0f172a);
            border: 1px solid #334155;
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 30px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        }
        .winner-price {
            font-size: 3.5rem;
            font-weight: 800;
            background: -webkit-linear-gradient(45deg, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        /* Buton Genel */
        .stButton > button {
            background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%);
            color: white !important;
            border: none;
            border-radius: 8px;
            height: 48px;
            font-weight: 600;
        }
        
        /* AI Box */
        .ai-box {
            background: #2d1b4e;
            border-left: 4px solid #a78bfa;
            padding: 20px;
            border-radius: 8px;
            margin-top: 20px;
        }

    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. YARDIMCI FONKSİYONLAR
# ==========================================
def format_tl(val):
    return f"{val:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")

def send_telegram_msg(token, chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
        requests.post(url, json=data)
        return True
    except: return False

def get_seasonal_advice(product_name, current_price):
    if not HAS_AI_LIBRARY or not GEMINI_API_KEY: return None
    genai.configure(api_key=GEMINI_API_KEY)
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        prompt = f"""
        Rol: Kıdemli Finans ve Teknoloji Analisti.
        Ürün: {product_name}
        Mevcut En İyi Fiyat: {current_price}
        
        Görev:
        1. Bu ürünün 6 aylık fiyat geçmişini (Launch cycle) simüle et.
        2. Şu an mevsimsel olarak "ALIM FIRSATI" mı yoksa "BEKLEME DÖNEMİ" mi?
        3. Net bir tavsiye ver (AL / BEKLE / SAT).
        
        Cevabı Türkçe, kısa ve profesyonel bir dille ver.
        """
        return model.generate_content(prompt).text
    except: return None

# ==========================================
# 2. SIDEBAR (PROFESSIONAL NAV)
# ==========================================
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; padding: 20px 0;">
            <h1 style="font-size: 2.5rem; margin:0;">⚡</h1>
            <h2 style="color:white; margin:0;">GhostDeal</h2>
            <p style="color:#64748b; font-size: 0.8rem; letter-spacing: 1px;">PRO EDITION v15.0</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    menu = st.radio(
        "NAVİGASYON", 
        ["🔎 Analiz & Arama", "🔥 Günün Fırsatları", "🔔 Fiyat Alarmı"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.info("🟢 Sistem Online\n\nAPI Durumu: Stabil")

# ==========================================
# 3. ANA SAYFA İÇERİĞİ
# ==========================================

# --- A: ARAMA & ANALİZ ---
if menu == "🔎 Analiz & Arama":
    st.markdown("<h2 style='color:#e2e8f0;'>🔎 Detaylı Piyasa Analizi</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([5, 1])
    with col1:
        query = st.text_input("Ürün Ara", placeholder="Örn: iPhone 15 Pro Max, Dyson V15...", label_visibility="collapsed")
    with col2:
        search_btn = st.button("ANALİZ ET", use_container_width=True)

    if search_btn and query:
        with st.spinner("🚀 Piyasa taranıyor, aksesuarlar eleniyor..."):
            df = search_all_sources(query, SERP_API_KEY, RAPID_API_KEY)
            st.session_state.search_results = df
            st.session_state.last_query = query
    
    if 'search_results' in st.session_state and not st.session_state.search_results.empty:
        df = st.session_state.search_results
        best = df.iloc[0]
        
        # 1. Winner Kartı
        st.markdown(f"""
        <div class="winner-section">
            <div>
                <span style="color:#94a3b8; letter-spacing:1px; font-size:0.9rem;">EN İYİ FİYAT</span>
                <div class="winner-price">{format_tl(best['Fiyat'])}</div>
                <div style="color:#cbd5e1; font-size:1.1rem; margin-top:5px;">{best['Ürün']}</div>
            </div>
            <div style="text-align:right;">
                <div style="margin-bottom:15px;">
                    <span style="background:#0f172a; border:1px solid #334155; padding:8px 16px; border-radius:20px; color:#38bdf8;">
                        Satıcı: {best['Satıcı']}
                    </span>
                </div>
                <a href="{best['Link']}" target="_blank" class="action-btn">ÜRÜNE GİT ↗</a>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 2. AI Analiz
        col_ai, _ = st.columns([2,3])
        if col_ai.button("✨ Yapay Zeka Stratejisi Al"):
            with st.spinner("🤖 Finansal veriler işleniyor..."):
                advice = get_seasonal_advice(st.session_state.last_query, format_tl(best['Fiyat']))
                if advice:
                    st.markdown(f"""
                    <div class="ai-box">
                        <h4 style="color:#a78bfa; margin-top:0;">🤖 GhostDeal Intelligence</h4>
                        <p style="color:#e2e8f0;">{advice}</p>
                    </div>
                    """, unsafe_allow_html=True)
        
        st.write("")
        st.markdown("### 📋 Diğer Seçenekler")
        st.dataframe(
            df[['Resim', 'Fiyat', 'Satıcı', 'Kaynak', 'Ürün', 'Link']],
            hide_index=True,
            use_container_width=True,
            column_config={
                "Fiyat": st.column_config.NumberColumn("Fiyat", format="%.2f TL"),
                "Link": st.column_config.LinkColumn("Link", display_text="Mağazaya Git"),
                "Resim": st.column_config.ImageColumn("Görsel", width="small"),
                "Ürün": st.column_config.TextColumn("Ürün Adı", width="large")
            }
        )

# --- B: FIRSAT VİTRİNİ (GRID SİSTEMİ) ---
elif menu == "🔥 Günün Fırsatları":
    col_head, col_btn = st.columns([4, 1])
    col_head.markdown("<h2 style='color:#e2e8f0;'>🔥 Amazon Fırsat Vitrini</h2>", unsafe_allow_html=True)
    
    if col_btn.button("YENİLE ↻", use_container_width=True):
        with st.spinner("📡 Global veriler çekiliyor (Turbo Mod)..."):
            deals_df = get_amazon_deals(RAPID_API_KEY, country="TR")
            st.session_state.deals_results = deals_df
            
    if 'deals_results' in st.session_state and not st.session_state.deals_results.empty:
        df = st.session_state.deals_results
        st.success(f"⚡ {len(df)} adet yüksek indirimli ürün listelendi.")
        
        # --- GRID LOOPS (4'lü Gruplar) ---
        num_columns = 4
        for i in range(0, len(df), num_columns):
            cols = st.columns(num_columns)
            batch = df.iloc[i:i+num_columns]
            
            for j, (_, row) in enumerate(batch.iterrows()):
                with cols[j]:
                    st.markdown(f"""
                    <div class="deal-card">
                        <span class="discount-badge">-{row['İndirim_Yazisi']}</span>
                        <div class="deal-img-container">
                            <img src="{row['Resim']}" class="deal-img">
                        </div>
                        <div class="deal-title" title="{row['Ürün']}">
                            {row['Ürün']}
                        </div>
                        <div class="price-wrapper">
                            <div class="price-old">{format_tl(row['Eski Fiyat'])}</div>
                            <div class="price-new">{format_tl(row['Fiyat'])}</div>
                        </div>
                        <a href="{row['Link']}" target="_blank" class="action-btn">İNCELE</a>
                    </div>
                    """, unsafe_allow_html=True)
                    
    elif 'deals_results' in st.session_state:
        st.warning("⚠️ Şu an kriterlere uygun fırsat bulunamadı. Lütfen daha sonra tekrar deneyin.")

# --- C: FİYAT ALARMI ---
elif menu == "🔔 Fiyat Alarmı":
    st.markdown("<h2 style='color:#e2e8f0;'>🔔 Otomatik Fiyat Takipçisi</h2>", unsafe_allow_html=True)
    
    with st.container():
        st.markdown("""
        <div style="background:#1e293b; padding:20px; border-radius:12px; border:1px solid #334155;">
            <p style="color:#94a3b8;">Ürün fiyatını sizin yerinize takip eder ve hedef fiyata düştüğünde Telegram'dan mesaj atar.</p>
        </div>
        <br>
        """, unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        target_product = c1.text_input("Takip Edilecek Ürün", placeholder="Örn: PlayStation 5 Slim")
        target_price = c2.number_input("Hedef Fiyat (TL)", min_value=0, value=20000)
        
        c3, c4 = st.columns(2)
        interval = c3.slider("Kontrol Sıklığı (Dakika)", 5, 60, 15)
        
        with st.expander("⚙️ Telegram Ayarları"):
            tg_token = st.text_input("Bot Token", type="password")
            tg_chat_id = st.text_input("Chat ID")
            
        if st.button("TAKİBİ BAŞLAT 🚀", use_container_width=True):
            if not target_product or not tg_token:
                st.error("Lütfen gerekli alanları doldurun.")
            else:
                status_box = st.empty()
                st.session_state.monitoring = True
                
                send_telegram_msg(tg_token, tg_chat_id, f"✅ <b>GhostDeal Başladı</b>\nÜrün: {target_product}\nHedef: {format_tl(target_price)}")
                
                while st.session_state.monitoring:
                    with status_box.container():
                        st.info(f"⏳ Son Kontrol: {time.strftime('%H:%M:%S')} - Sistem Çalışıyor...")
                        
                        df = search_all_sources(target_product, SERP_API_KEY, RAPID_API_KEY)
                        if not df.empty:
                            best = df.iloc[0]
                            curr = best['Fiyat']
                            
                            if curr <= target_price:
                                msg = f"🚨 <b>FİYAT DÜŞTÜ!</b>\n\n📦 {best['Ürün']}\n💰 <b>{format_tl(curr)}</b>\n🛒 {best['Satıcı']}\n🔗 {best['Link']}"
                                send_telegram_msg(tg_token, tg_chat_id, msg)
                                st.success("🎉 HEDEF YAKALANDI! Mesaj gönderildi.")
                                st.balloons()
                                st.session_state.monitoring = False
                                break
                    time.sleep(interval * 60)