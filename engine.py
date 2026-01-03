import requests
from serpapi import GoogleSearch
import pandas as pd
import re
import time

# --- FİYAT TEMİZLEME ---
def clean_price(price):
    if not price: return 0.0
    try:
        if isinstance(price, (int, float)): return float(price)
        price_str = str(price)
        # Sadece rakam, nokta ve virgül kalsın
        clean = re.sub(r'[^\d.,]', '', price_str)
        # Format düzeltme (1.000,00 -> 1000.0)
        if ',' in clean and '.' in clean:
            if clean.find('.') < clean.find(','): clean = clean.replace('.', '').replace(',', '.')
            else: clean = clean.replace(',', '')
        elif ',' in clean: clean = clean.replace(',', '.')
        return float(clean)
    except: return 0.0

# --- AKILLI TEMİZLİK (Aksesuar & Çöp Engelleyici) ---
def smart_clean_results(df, query):
    if df.empty: return df
    
    # 1. Yasaklı Kelime Filtresi (Örn: AirPods ararken Kılıf gelmesin)
    forbidden_words = ["kılıf", "case", "kapak", "silikon", "koruyucu", "cam", "jelatin", "askı", "tutucu", "stand", "kablo", "adaptör", "şarj"]
    query_lower = query.lower()
    
    # Eğer kullanıcı özellikle bu kelimeleri aramadıysa filtrele
    if not any(word in query_lower for word in forbidden_words):
        pattern = '|'.join(forbidden_words)
        df = df[~df['Ürün'].str.lower().str.contains(pattern, na=False)]
    
    # 2. Fiyat Mantığı (Ortalamanın %50 altı çöptür)
    if not df.empty:
        market_price = df['Fiyat'].median()
        threshold = market_price * 0.50 
        df = df[df['Fiyat'] >= threshold]
    
    # 3. Sayısal Eşleşme (17 ararken 13 gelmesin)
    query_numbers = re.findall(r'\d+', query)
    if query_numbers:
        for num in query_numbers:
            df = df[df['Ürün'].str.contains(num, case=False, na=False)]
            
    return df

# --- KAYNAK 1: GOOGLE (SERPAPI) ---
def search_serpapi(query, api_key):
    if not api_key: return []
    try:
        params = {"engine": "google_shopping", "q": query, "hl": "tr", "gl": "tr", "api_key": api_key}
        search = GoogleSearch(params)
        results = search.get_dict().get("shopping_results", [])
        products = []
        for item in results:
            link = item.get("link") or item.get("product_link") or item.get("url")
            products.append({
                "Ürün": item.get("title"),
                "Fiyat": clean_price(item.get("price")),
                "Satıcı": item.get("source"),
                "Link": link,
                "Kaynak": "Google",
                "Resim": item.get("thumbnail")
            })
        return products
    except Exception as e:
        print(f"SerpApi Hata: {e}")
        return []

# --- KAYNAK 2: AMAZON ARAMA (RAPIDAPI) ---
def search_rapidapi(query, api_key):
    if not api_key: return []
    url = "https://real-time-amazon-data.p.rapidapi.com/search"
    querystring = {"query": query, "country": "TR", "sort_by": "RELEVANCE", "page": "1"}
    headers = {"X-RapidAPI-Key": api_key, "X-RapidAPI-Host": "real-time-amazon-data.p.rapidapi.com"}
    try:
        response = requests.get(url, headers=headers, params=querystring)
        if response.status_code != 200: return []
        data = response.json()
        results = data.get("data", {}).get("products", [])
        products = []
        for item in results:
            price = item.get("product_price")
            link = item.get("product_url") or item.get("url")
            products.append({
                "Ürün": item.get("product_title"),
                "Fiyat": clean_price(price),
                "Satıcı": "Amazon TR",
                "Link": link,
                "Kaynak": "Amazon",
                "Resim": item.get("product_photo")
            })
        return products
    except: return []

# --- KAYNAK 3: AMAZON FIRSATLARI (HİBRİT HESAPLAMA) ---
def get_amazon_deals(api_key, country="TR"):
    if not api_key: return pd.DataFrame()
    
    url = "https://real-time-amazon-data.p.rapidapi.com/deals-v2"
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "real-time-amazon-data.p.rapidapi.com"
    }
    
    all_deals = []
    
    # TURBO MOD: 10 Sayfa Tara (Daha çok veri)
    for page in range(1, 2):
        querystring = {
            "country": country, 
            "min_product_star_rating": "ALL", 
            "price_range": "ALL", 
            "discount_range": "ALL",
            "page": str(page)
        }

        try:
            response = requests.get(url, headers=headers, params=querystring)
            data = response.json()
            deals = data.get("data", {}).get("deals", [])
            
            if not deals: break 
            
            for d in deals:
                title = d.get("deal_title") or d.get("product_title")
                
                img = d.get("deal_photo")
                if not img: img = d.get("product_photo")
                if not img: img = "https://via.placeholder.com/150?text=Resim+Yok"
                
                price_val = clean_price(d.get("deal_price", {}).get("amount", "0"))
                old_price_val = clean_price(d.get("list_price", {}).get("amount", "0"))
                
                # --- HİBRİT İNDİRİM HESABI ---
                # 1. Manuel Hesapla: (Eski - Yeni) / Eski
                manual_savings = 0
                if old_price_val > price_val and old_price_val > 0:
                    manual_savings = int(((old_price_val - price_val) / old_price_val) * 100)
                
                # 2. API Verisi
                api_savings = d.get("savings_percentage", 0)
                
                # Hangisi büyükse onu al (Veri kurtarma)
                final_savings = max(manual_savings, api_savings)
                
                # %1 altı indirimleri gösterme
                if final_savings < 1: continue
                
                link = d.get("product_url") or d.get("deal_url") or "#"

                all_deals.append({
                    "Ürün": title,
                    "Fiyat": price_val,
                    "Eski Fiyat": old_price_val,
                    "İndirim_Oranı": final_savings, 
                    "İndirim_Yazisi": f"%{final_savings}", 
                    "Resim": img,
                    "Link": link
                })
            time.sleep(0.2)
        except: break
            
    df = pd.DataFrame(all_deals)
    
    if not df.empty:
        # 1. İkizleri Temizle
        df = df.sort_values(by=['Fiyat'], ascending=True)
        df = df.drop_duplicates(subset=['Ürün'], keep='first')
        
        # 2. Sıralama (Büyükten Küçüğe)
        df = df.sort_values(by="İndirim_Oranı", ascending=False)
        df = df.reset_index(drop=True)
        
    return df

# --- ANA MOTOR ---
def search_all_sources(query, serp_key, rapid_key):
    r1 = search_serpapi(query, serp_key)
    r2 = search_rapidapi(query, rapid_key)
    all_results = r1 + r2
    if not all_results: return pd.DataFrame()
    df = pd.DataFrame(all_results)
    df = df[df['Fiyat'] > 0]
    df = smart_clean_results(df, query)
    df = df.sort_values(by="Fiyat", ascending=True)
    return df
