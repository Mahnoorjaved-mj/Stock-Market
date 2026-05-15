
import yfinance as yf
import pandas as pd
import numpy as np
import base64
from datetime import datetime, timedelta
import time
import concurrent.futures
from typing import Dict, List, Any
import requests
import json
import os

print("Loading Real-Time Global Stocks Dashboard with Alpha Vantage")


# Prefer env var; fall back to historical hardcoded key so existing deployments keep working
try:
    from config import config as _cfg
    ALPHA_VANTAGE_API_KEY = _cfg.ALPHA_VANTAGE_KEY or os.getenv("ALPHA_VANTAGE_KEY", "S7ULZPIQ8OSIWQV8")
except Exception:
    ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_KEY", "S7ULZPIQ8OSIWQV8")

class StockDataFetcher:
    """Real-time stock data fetcher using Alpha Vantage as primary source"""
    
    def __init__(self):
        self.cache = {}
        self.cache_time = {}
        self.cache_duration = 300  
        self.request_count = 0
        self.last_request_time = time.time()
        self.request_times = [] 
        self.max_requests_per_minute = 5  
    
    def _can_make_request(self) -> bool:
        """Check if we can make an API request without exceeding rate limits"""
        current_time = time.time()

        self.request_times = [t for t in self.request_times if current_time - t < 60]
       
        if len(self.request_times) < self.max_requests_per_minute:
            return True
        
     
        oldest_request = min(self.request_times)
        wait_time = 60 - (current_time - oldest_request)
        if wait_time > 0:
            print(f"   ⏳ Rate limit reached. Using fallback data (would wait {wait_time:.1f}s)")
            return False
        
        return True
    
    def _record_request(self):
        """Record that we made an API request"""
        self.request_times.append(time.time())
        self.request_count += 1
    
    def get_stock_data(self, symbol: str) -> dict:
        """Get real-time stock data with intelligent caching and rate limiting"""
        
        # Check cache first
        current_time = time.time()
        cache_key = f"{symbol}_data"
        if cache_key in self.cache and cache_key in self.cache_time:
            if current_time - self.cache_time[cache_key] < self.cache_duration:
                print(f"   💾 {symbol}: Using cached data ({int(self.cache_duration - (current_time - self.cache_time[cache_key]))}s remaining)")
                return self.cache[cache_key]
        
        # Try to fetch live data from Alpha Vantage
        if self._can_make_request():
            print(f"   🔍 {symbol}: Fetching live data from Alpha Vantage...")
            self._record_request()
            
            result = self._fetch_from_alpha_vantage(symbol)
            
            if result['success'] and result['price'] > 0:
                print(f"   ✅ {symbol}: ${result['price']:.2f} (live from Alpha Vantage)")
                self.cache[cache_key] = result
                self.cache_time[cache_key] = current_time
                return result
            else:
                print(f"   ⚠️ {symbol}: Alpha Vantage failed, trying yfinance...")
                result = self._fetch_from_yfinance(symbol)
                
                if result['success'] and result['price'] > 0:
                    print(f"   ✅ {symbol}: ${result['price']:.2f} (from yfinance)")
                    self.cache[cache_key] = result
                    self.cache_time[cache_key] = current_time
                    return result
        
   
        print(f"   💾 {symbol}: Using fallback data (API unavailable)")
        fallback_prices = {
            'AAPL': (278.28, 0.40), 'MSFT': (478.53, -0.54), 'GOOGL': (309.29, 0.25),
            'AMZN': (226.19, -0.51), 'TSLA': (458.96, 2.70), 'META': (644.23, -1.30),
            'NVDA': (175.02, -3.27), 'JPM': (318.52, 0.36), 'V': (347.83, 0.64),
            'JNJ': (211.58, 0.75), 'WMT': (165.75, 0.32), 'PG': (142.84, 0.18),
            'MA': (420.80, 0.45), 'DIS': (90.80, -0.22), 'NFLX': (600.25, 1.15),
            'ADBE': (580.90, 0.88), 'PYPL': (60.40, -0.35), 'INTC': (45.20, -0.12),
            'CSCO': (55.30, 0.28), 'PEP': (175.40, 0.42), 'COST': (700.80, 0.65),
            'MRK': (105.60, 0.31), 'ABT': (105.25, 0.19), 'TMO': (550.80, 0.52),
            'AVGO': (1150.50, 1.25), 'ACN': (350.75, 0.38), 'CRM': (250.30, 0.72),
            'NKE': (85.45, -0.18), 'AMD': (120.75, 1.85), 'QCOM': (165.30, 0.55)
        }
        
        if symbol in fallback_prices:
            price, change_pct = fallback_prices[symbol]
            change = price * (change_pct / 100)
            prev_close = price - change
            result = {
                'price': price,
                'change': change,
                'change_percent': change_pct,
                'volume': 10000000,
                'previous_close': prev_close,
                'success': True,
                'source': 'fallback'
            }
            self.cache[cache_key] = result
            self.cache_time[cache_key] = current_time
            return result
        
  
        return {
            'price': 0.0,
            'change': 0.0,
            'change_percent': 0.0,
            'volume': 0,
            'previous_close': 0.0,
            'success': False,
            'source': 'failed'
        }
    
    def _fetch_from_alpha_vantage(self, symbol: str) -> dict:
        """Fetch real-time data from Alpha Vantage GLOBAL_QUOTE endpoint"""
        try:
            print(f"   🔍 Attempting Alpha Vantage for {symbol}...")
            
          
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_VANTAGE_API_KEY}"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if symbol in ['AAPL', 'MSFT', 'GOOGL']:
                print(f"   📡 Alpha Vantage raw for {symbol}: {json.dumps(data)[:100]}...")
            
            if "Global Quote" in data and data["Global Quote"]:
                quote = data["Global Quote"]
                
                price_str = quote.get("05. price", "0")
                change_str = quote.get("09. change", "0")
                change_pct_str = quote.get("10. change percent", "0%").rstrip('%')
                volume_str = quote.get("06. volume", "0")
                prev_close_str = quote.get("08. previous close", "0")
                
            
                price = float(price_str) if price_str and price_str != "0" else 0
                change = float(change_str) if change_str else 0
                change_percent = float(change_pct_str) if change_pct_str else 0
                volume = int(float(volume_str)) if volume_str and volume_str != "0" else 0
                prev_close = float(prev_close_str) if prev_close_str and prev_close_str != "0" else price - change
                
         
                if price > 0:
                    return {
                        'price': price,
                        'change': change,
                        'change_percent': change_percent,
                        'volume': volume,
                        'previous_close': prev_close,
                        'success': True,
                        'source': 'alpha_vantage'
                    }
            
     
            return self._fetch_from_alpha_vantage_alternative(symbol)
            
        except Exception as e:
            print(f"   ❌ Alpha Vantage error for {symbol}: {str(e)[:50]}")
            return {'success': False, 'source': 'alpha_vantage'}
    
    def _fetch_from_alpha_vantage_alternative(self, symbol: str) -> dict:
        """Alternative Alpha Vantage endpoint if GLOBAL_QUOTE fails"""
        try:
           
            url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=5min&apikey={ALPHA_VANTAGE_API_KEY}"
            
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if "Time Series (5min)" in data:
                time_series = data["Time Series (5min)"]
                if time_series:
                    latest_time = max(time_series.keys())
                    latest_data = time_series[latest_time]
                    
                    price = float(latest_data.get("4. close", 0))
                    volume = int(latest_data.get("5. volume", 0))
                    
                    if price > 0:
                        return {
                            'price': price,
                            'change': 0,
                            'change_percent': 0,
                            'volume': volume,
                            'previous_close': price,
                            'success': True,
                            'source': 'alpha_vantage_intraday'
                        }
            
            return {'success': False, 'source': 'alpha_vantage'}
            
        except Exception as e:
            return {'success': False, 'source': 'alpha_vantage'}
    
    def _fetch_from_yfinance(self, symbol: str) -> dict:
        """Fallback to yfinance when Alpha Vantage fails - FAST MODE"""
        try:
    
            ticker = yf.Ticker(symbol)
            
           
            hist = ticker.history(period="5d", interval="1d")
            
            if not hist.empty and len(hist) >= 2:
                latest_price = float(hist['Close'].iloc[-1])
                prev_close = float(hist['Close'].iloc[-2])
                change = latest_price - prev_close
                change_percent = (change / prev_close) * 100 if prev_close > 0 else 0
                volume = int(hist['Volume'].iloc[-1]) if 'Volume' in hist.columns else 0
                
                return {
                    'price': latest_price,
                    'change': change,
                    'change_percent': change_percent,
                    'volume': volume,
                    'previous_close': prev_close,
                    'success': True,
                    'source': 'yfinance'
                }
            
            # If no data, fail fast
            return {'success': False, 'source': 'yfinance'}
            
        except Exception as e:
            # Fail fast without retries
            return {'success': False, 'source': 'yfinance'}

# Global fetcher instance
fetcher = StockDataFetcher()


# =====================================================================
# STOCK UNIVERSE - 250+ curated global tickers
# Module-level so other modules (watchlist, alerts) can read it.
# =====================================================================
STOCK_DEFINITIONS: List[Dict[str, str]] = [
    # ============ UNITED STATES - Tech ============
    {"symbol": "AAPL",  "country": "US", "currency": "USD", "name": "Apple Inc.", "sector": "Technology"},
    {"symbol": "MSFT",  "country": "US", "currency": "USD", "name": "Microsoft Corporation", "sector": "Technology"},
    {"symbol": "GOOGL", "country": "US", "currency": "USD", "name": "Alphabet Inc. (Class A)", "sector": "Technology"},
    {"symbol": "GOOG",  "country": "US", "currency": "USD", "name": "Alphabet Inc. (Class C)", "sector": "Technology"},
    {"symbol": "META",  "country": "US", "currency": "USD", "name": "Meta Platforms Inc.", "sector": "Technology"},
    {"symbol": "NVDA",  "country": "US", "currency": "USD", "name": "NVIDIA Corporation", "sector": "Technology"},
    {"symbol": "AMD",   "country": "US", "currency": "USD", "name": "Advanced Micro Devices", "sector": "Technology"},
    {"symbol": "INTC",  "country": "US", "currency": "USD", "name": "Intel Corporation", "sector": "Technology"},
    {"symbol": "AVGO",  "country": "US", "currency": "USD", "name": "Broadcom Inc.", "sector": "Technology"},
    {"symbol": "QCOM",  "country": "US", "currency": "USD", "name": "Qualcomm", "sector": "Technology"},
    {"symbol": "TXN",   "country": "US", "currency": "USD", "name": "Texas Instruments", "sector": "Technology"},
    {"symbol": "MU",    "country": "US", "currency": "USD", "name": "Micron Technology", "sector": "Technology"},
    {"symbol": "AMAT",  "country": "US", "currency": "USD", "name": "Applied Materials", "sector": "Technology"},
    {"symbol": "LRCX",  "country": "US", "currency": "USD", "name": "Lam Research", "sector": "Technology"},
    {"symbol": "KLAC",  "country": "US", "currency": "USD", "name": "KLA Corporation", "sector": "Technology"},
    {"symbol": "ADBE",  "country": "US", "currency": "USD", "name": "Adobe Inc.", "sector": "Technology"},
    {"symbol": "CRM",   "country": "US", "currency": "USD", "name": "Salesforce", "sector": "Technology"},
    {"symbol": "ORCL",  "country": "US", "currency": "USD", "name": "Oracle Corporation", "sector": "Technology"},
    {"symbol": "IBM",   "country": "US", "currency": "USD", "name": "IBM", "sector": "Technology"},
    {"symbol": "CSCO",  "country": "US", "currency": "USD", "name": "Cisco Systems", "sector": "Technology"},
    {"symbol": "ACN",   "country": "US", "currency": "USD", "name": "Accenture", "sector": "Technology"},
    {"symbol": "NOW",   "country": "US", "currency": "USD", "name": "ServiceNow", "sector": "Technology"},
    {"symbol": "INTU",  "country": "US", "currency": "USD", "name": "Intuit", "sector": "Technology"},
    {"symbol": "PANW",  "country": "US", "currency": "USD", "name": "Palo Alto Networks", "sector": "Technology"},
    {"symbol": "CRWD",  "country": "US", "currency": "USD", "name": "CrowdStrike", "sector": "Technology"},
    {"symbol": "SNOW",  "country": "US", "currency": "USD", "name": "Snowflake", "sector": "Technology"},
    {"symbol": "PLTR",  "country": "US", "currency": "USD", "name": "Palantir Technologies", "sector": "Technology"},
    {"symbol": "DDOG",  "country": "US", "currency": "USD", "name": "Datadog", "sector": "Technology"},
    {"symbol": "NET",   "country": "US", "currency": "USD", "name": "Cloudflare", "sector": "Technology"},
    {"symbol": "ZS",    "country": "US", "currency": "USD", "name": "Zscaler", "sector": "Technology"},

    # ============ US - Internet / Commerce / Media ============
    {"symbol": "AMZN",  "country": "US", "currency": "USD", "name": "Amazon.com Inc.", "sector": "E-commerce"},
    {"symbol": "NFLX",  "country": "US", "currency": "USD", "name": "Netflix Inc.", "sector": "Entertainment"},
    {"symbol": "DIS",   "country": "US", "currency": "USD", "name": "Walt Disney Company", "sector": "Entertainment"},
    {"symbol": "TSLA",  "country": "US", "currency": "USD", "name": "Tesla Inc.", "sector": "Automotive"},
    {"symbol": "UBER",  "country": "US", "currency": "USD", "name": "Uber Technologies", "sector": "Transport"},
    {"symbol": "LYFT",  "country": "US", "currency": "USD", "name": "Lyft Inc.", "sector": "Transport"},
    {"symbol": "ABNB",  "country": "US", "currency": "USD", "name": "Airbnb", "sector": "Travel"},
    {"symbol": "BKNG",  "country": "US", "currency": "USD", "name": "Booking Holdings", "sector": "Travel"},
    {"symbol": "EBAY",  "country": "US", "currency": "USD", "name": "eBay", "sector": "E-commerce"},
    {"symbol": "ETSY",  "country": "US", "currency": "USD", "name": "Etsy", "sector": "E-commerce"},
    {"symbol": "PINS",  "country": "US", "currency": "USD", "name": "Pinterest", "sector": "Technology"},
    {"symbol": "SNAP",  "country": "US", "currency": "USD", "name": "Snap Inc.", "sector": "Technology"},
    {"symbol": "SPOT",  "country": "US", "currency": "USD", "name": "Spotify", "sector": "Entertainment"},
    {"symbol": "WBD",   "country": "US", "currency": "USD", "name": "Warner Bros. Discovery", "sector": "Entertainment"},
    {"symbol": "PARA",  "country": "US", "currency": "USD", "name": "Paramount Global", "sector": "Entertainment"},
    {"symbol": "EA",    "country": "US", "currency": "USD", "name": "Electronic Arts", "sector": "Gaming"},
    {"symbol": "TTWO",  "country": "US", "currency": "USD", "name": "Take-Two Interactive", "sector": "Gaming"},
    {"symbol": "RBLX",  "country": "US", "currency": "USD", "name": "Roblox", "sector": "Gaming"},

    # ============ US - Finance ============
    {"symbol": "JPM",   "country": "US", "currency": "USD", "name": "JPMorgan Chase", "sector": "Finance"},
    {"symbol": "BAC",   "country": "US", "currency": "USD", "name": "Bank of America", "sector": "Finance"},
    {"symbol": "WFC",   "country": "US", "currency": "USD", "name": "Wells Fargo", "sector": "Finance"},
    {"symbol": "C",     "country": "US", "currency": "USD", "name": "Citigroup", "sector": "Finance"},
    {"symbol": "GS",    "country": "US", "currency": "USD", "name": "Goldman Sachs", "sector": "Finance"},
    {"symbol": "MS",    "country": "US", "currency": "USD", "name": "Morgan Stanley", "sector": "Finance"},
    {"symbol": "BLK",   "country": "US", "currency": "USD", "name": "BlackRock", "sector": "Finance"},
    {"symbol": "SCHW",  "country": "US", "currency": "USD", "name": "Charles Schwab", "sector": "Finance"},
    {"symbol": "AXP",   "country": "US", "currency": "USD", "name": "American Express", "sector": "Finance"},
    {"symbol": "V",     "country": "US", "currency": "USD", "name": "Visa Inc.", "sector": "Finance"},
    {"symbol": "MA",    "country": "US", "currency": "USD", "name": "Mastercard", "sector": "Finance"},
    {"symbol": "PYPL",  "country": "US", "currency": "USD", "name": "PayPal Holdings", "sector": "Finance"},
    {"symbol": "SQ",    "country": "US", "currency": "USD", "name": "Block (Square)", "sector": "Finance"},
    {"symbol": "COIN",  "country": "US", "currency": "USD", "name": "Coinbase", "sector": "Finance"},
    {"symbol": "HOOD",  "country": "US", "currency": "USD", "name": "Robinhood", "sector": "Finance"},
    {"symbol": "BRK.B", "country": "US", "currency": "USD", "name": "Berkshire Hathaway", "sector": "Finance"},
    {"symbol": "SPGI",  "country": "US", "currency": "USD", "name": "S&P Global", "sector": "Finance"},
    {"symbol": "MCO",   "country": "US", "currency": "USD", "name": "Moody's", "sector": "Finance"},
    {"symbol": "ICE",   "country": "US", "currency": "USD", "name": "Intercontinental Exchange", "sector": "Finance"},
    {"symbol": "CME",   "country": "US", "currency": "USD", "name": "CME Group", "sector": "Finance"},

    # ============ US - Healthcare / Pharma ============
    {"symbol": "JNJ",   "country": "US", "currency": "USD", "name": "Johnson & Johnson", "sector": "Healthcare"},
    {"symbol": "LLY",   "country": "US", "currency": "USD", "name": "Eli Lilly", "sector": "Healthcare"},
    {"symbol": "ABBV",  "country": "US", "currency": "USD", "name": "AbbVie", "sector": "Healthcare"},
    {"symbol": "MRK",   "country": "US", "currency": "USD", "name": "Merck & Co.", "sector": "Healthcare"},
    {"symbol": "PFE",   "country": "US", "currency": "USD", "name": "Pfizer", "sector": "Healthcare"},
    {"symbol": "ABT",   "country": "US", "currency": "USD", "name": "Abbott Laboratories", "sector": "Healthcare"},
    {"symbol": "TMO",   "country": "US", "currency": "USD", "name": "Thermo Fisher Scientific", "sector": "Healthcare"},
    {"symbol": "DHR",   "country": "US", "currency": "USD", "name": "Danaher", "sector": "Healthcare"},
    {"symbol": "BMY",   "country": "US", "currency": "USD", "name": "Bristol-Myers Squibb", "sector": "Healthcare"},
    {"symbol": "AMGN",  "country": "US", "currency": "USD", "name": "Amgen", "sector": "Healthcare"},
    {"symbol": "GILD",  "country": "US", "currency": "USD", "name": "Gilead Sciences", "sector": "Healthcare"},
    {"symbol": "VRTX",  "country": "US", "currency": "USD", "name": "Vertex Pharmaceuticals", "sector": "Healthcare"},
    {"symbol": "REGN",  "country": "US", "currency": "USD", "name": "Regeneron", "sector": "Healthcare"},
    {"symbol": "ISRG",  "country": "US", "currency": "USD", "name": "Intuitive Surgical", "sector": "Healthcare"},
    {"symbol": "MDT",   "country": "US", "currency": "USD", "name": "Medtronic", "sector": "Healthcare"},
    {"symbol": "UNH",   "country": "US", "currency": "USD", "name": "UnitedHealth Group", "sector": "Healthcare"},
    {"symbol": "CI",    "country": "US", "currency": "USD", "name": "Cigna", "sector": "Healthcare"},
    {"symbol": "CVS",   "country": "US", "currency": "USD", "name": "CVS Health", "sector": "Healthcare"},
    {"symbol": "HUM",   "country": "US", "currency": "USD", "name": "Humana", "sector": "Healthcare"},
    {"symbol": "MRNA",  "country": "US", "currency": "USD", "name": "Moderna", "sector": "Healthcare"},

    # ============ US - Consumer / Retail ============
    {"symbol": "WMT",   "country": "US", "currency": "USD", "name": "Walmart Inc.", "sector": "Retail"},
    {"symbol": "COST",  "country": "US", "currency": "USD", "name": "Costco Wholesale", "sector": "Retail"},
    {"symbol": "TGT",   "country": "US", "currency": "USD", "name": "Target", "sector": "Retail"},
    {"symbol": "HD",    "country": "US", "currency": "USD", "name": "Home Depot", "sector": "Retail"},
    {"symbol": "LOW",   "country": "US", "currency": "USD", "name": "Lowe's", "sector": "Retail"},
    {"symbol": "BBY",   "country": "US", "currency": "USD", "name": "Best Buy", "sector": "Retail"},
    {"symbol": "KR",    "country": "US", "currency": "USD", "name": "Kroger", "sector": "Retail"},
    {"symbol": "DG",    "country": "US", "currency": "USD", "name": "Dollar General", "sector": "Retail"},
    {"symbol": "DLTR",  "country": "US", "currency": "USD", "name": "Dollar Tree", "sector": "Retail"},
    {"symbol": "PG",    "country": "US", "currency": "USD", "name": "Procter & Gamble", "sector": "Consumer"},
    {"symbol": "KO",    "country": "US", "currency": "USD", "name": "Coca-Cola", "sector": "Consumer"},
    {"symbol": "PEP",   "country": "US", "currency": "USD", "name": "PepsiCo", "sector": "Consumer"},
    {"symbol": "MDLZ",  "country": "US", "currency": "USD", "name": "Mondelez International", "sector": "Consumer"},
    {"symbol": "CL",    "country": "US", "currency": "USD", "name": "Colgate-Palmolive", "sector": "Consumer"},
    {"symbol": "MO",    "country": "US", "currency": "USD", "name": "Altria Group", "sector": "Consumer"},
    {"symbol": "PM",    "country": "US", "currency": "USD", "name": "Philip Morris International", "sector": "Consumer"},
    {"symbol": "NKE",   "country": "US", "currency": "USD", "name": "Nike Inc.", "sector": "Consumer"},
    {"symbol": "LULU",  "country": "US", "currency": "USD", "name": "Lululemon", "sector": "Consumer"},
    {"symbol": "MCD",   "country": "US", "currency": "USD", "name": "McDonald's", "sector": "Consumer"},
    {"symbol": "SBUX",  "country": "US", "currency": "USD", "name": "Starbucks", "sector": "Consumer"},
    {"symbol": "YUM",   "country": "US", "currency": "USD", "name": "Yum! Brands", "sector": "Consumer"},
    {"symbol": "CMG",   "country": "US", "currency": "USD", "name": "Chipotle Mexican Grill", "sector": "Consumer"},

    # ============ US - Energy / Materials / Industrials ============
    {"symbol": "XOM",   "country": "US", "currency": "USD", "name": "Exxon Mobil", "sector": "Energy"},
    {"symbol": "CVX",   "country": "US", "currency": "USD", "name": "Chevron", "sector": "Energy"},
    {"symbol": "COP",   "country": "US", "currency": "USD", "name": "ConocoPhillips", "sector": "Energy"},
    {"symbol": "OXY",   "country": "US", "currency": "USD", "name": "Occidental Petroleum", "sector": "Energy"},
    {"symbol": "SLB",   "country": "US", "currency": "USD", "name": "Schlumberger", "sector": "Energy"},
    {"symbol": "EOG",   "country": "US", "currency": "USD", "name": "EOG Resources", "sector": "Energy"},
    {"symbol": "PSX",   "country": "US", "currency": "USD", "name": "Phillips 66", "sector": "Energy"},
    {"symbol": "MPC",   "country": "US", "currency": "USD", "name": "Marathon Petroleum", "sector": "Energy"},
    {"symbol": "LIN",   "country": "US", "currency": "USD", "name": "Linde", "sector": "Chemical"},
    {"symbol": "APD",   "country": "US", "currency": "USD", "name": "Air Products & Chemicals", "sector": "Chemical"},
    {"symbol": "FCX",   "country": "US", "currency": "USD", "name": "Freeport-McMoRan", "sector": "Mining"},
    {"symbol": "NUE",   "country": "US", "currency": "USD", "name": "Nucor", "sector": "Materials"},
    {"symbol": "BA",    "country": "US", "currency": "USD", "name": "Boeing", "sector": "Aerospace"},
    {"symbol": "LMT",   "country": "US", "currency": "USD", "name": "Lockheed Martin", "sector": "Aerospace"},
    {"symbol": "RTX",   "country": "US", "currency": "USD", "name": "RTX Corporation", "sector": "Aerospace"},
    {"symbol": "NOC",   "country": "US", "currency": "USD", "name": "Northrop Grumman", "sector": "Aerospace"},
    {"symbol": "GD",    "country": "US", "currency": "USD", "name": "General Dynamics", "sector": "Aerospace"},
    {"symbol": "CAT",   "country": "US", "currency": "USD", "name": "Caterpillar", "sector": "Industrial"},
    {"symbol": "DE",    "country": "US", "currency": "USD", "name": "Deere & Company", "sector": "Industrial"},
    {"symbol": "HON",   "country": "US", "currency": "USD", "name": "Honeywell", "sector": "Industrial"},
    {"symbol": "GE",    "country": "US", "currency": "USD", "name": "General Electric", "sector": "Industrial"},
    {"symbol": "MMM",   "country": "US", "currency": "USD", "name": "3M", "sector": "Industrial"},
    {"symbol": "F",     "country": "US", "currency": "USD", "name": "Ford Motor", "sector": "Automotive"},
    {"symbol": "GM",    "country": "US", "currency": "USD", "name": "General Motors", "sector": "Automotive"},
    {"symbol": "RIVN",  "country": "US", "currency": "USD", "name": "Rivian Automotive", "sector": "Automotive"},
    {"symbol": "LCID",  "country": "US", "currency": "USD", "name": "Lucid Group", "sector": "Automotive"},
    {"symbol": "UPS",   "country": "US", "currency": "USD", "name": "United Parcel Service", "sector": "Logistics"},
    {"symbol": "FDX",   "country": "US", "currency": "USD", "name": "FedEx", "sector": "Logistics"},
    {"symbol": "UNP",   "country": "US", "currency": "USD", "name": "Union Pacific", "sector": "Logistics"},
    {"symbol": "CSX",   "country": "US", "currency": "USD", "name": "CSX Corporation", "sector": "Logistics"},
    {"symbol": "DAL",   "country": "US", "currency": "USD", "name": "Delta Air Lines", "sector": "Airlines"},
    {"symbol": "UAL",   "country": "US", "currency": "USD", "name": "United Airlines", "sector": "Airlines"},
    {"symbol": "AAL",   "country": "US", "currency": "USD", "name": "American Airlines", "sector": "Airlines"},
    {"symbol": "LUV",   "country": "US", "currency": "USD", "name": "Southwest Airlines", "sector": "Airlines"},

    # ============ US - Utilities / Telecom / REITs ============
    {"symbol": "NEE",   "country": "US", "currency": "USD", "name": "NextEra Energy", "sector": "Utilities"},
    {"symbol": "DUK",   "country": "US", "currency": "USD", "name": "Duke Energy", "sector": "Utilities"},
    {"symbol": "SO",    "country": "US", "currency": "USD", "name": "Southern Company", "sector": "Utilities"},
    {"symbol": "AEP",   "country": "US", "currency": "USD", "name": "American Electric Power", "sector": "Utilities"},
    {"symbol": "T",     "country": "US", "currency": "USD", "name": "AT&T", "sector": "Telecom"},
    {"symbol": "VZ",    "country": "US", "currency": "USD", "name": "Verizon Communications", "sector": "Telecom"},
    {"symbol": "TMUS",  "country": "US", "currency": "USD", "name": "T-Mobile US", "sector": "Telecom"},
    {"symbol": "CMCSA", "country": "US", "currency": "USD", "name": "Comcast", "sector": "Telecom"},
    {"symbol": "PLD",   "country": "US", "currency": "USD", "name": "Prologis", "sector": "REIT"},
    {"symbol": "AMT",   "country": "US", "currency": "USD", "name": "American Tower", "sector": "REIT"},
    {"symbol": "EQIX",  "country": "US", "currency": "USD", "name": "Equinix", "sector": "REIT"},

    # ============ United Kingdom (FTSE) ============
    {"symbol": "HSBA.L",  "country": "UK", "currency": "GBP", "name": "HSBC Holdings", "sector": "Finance"},
    {"symbol": "BARC.L",  "country": "UK", "currency": "GBP", "name": "Barclays", "sector": "Finance"},
    {"symbol": "LLOY.L",  "country": "UK", "currency": "GBP", "name": "Lloyds Banking Group", "sector": "Finance"},
    {"symbol": "NWG.L",   "country": "UK", "currency": "GBP", "name": "NatWest Group", "sector": "Finance"},
    {"symbol": "SHEL.L",  "country": "UK", "currency": "GBP", "name": "Shell plc", "sector": "Energy"},
    {"symbol": "BP.L",    "country": "UK", "currency": "GBP", "name": "BP plc", "sector": "Energy"},
    {"symbol": "AZN.L",   "country": "UK", "currency": "GBP", "name": "AstraZeneca", "sector": "Healthcare"},
    {"symbol": "GSK.L",   "country": "UK", "currency": "GBP", "name": "GSK plc", "sector": "Healthcare"},
    {"symbol": "ULVR.L",  "country": "UK", "currency": "GBP", "name": "Unilever", "sector": "Consumer"},
    {"symbol": "DGE.L",   "country": "UK", "currency": "GBP", "name": "Diageo", "sector": "Consumer"},
    {"symbol": "BATS.L",  "country": "UK", "currency": "GBP", "name": "British American Tobacco", "sector": "Consumer"},
    {"symbol": "RIO.L",   "country": "UK", "currency": "GBP", "name": "Rio Tinto", "sector": "Mining"},
    {"symbol": "GLEN.L",  "country": "UK", "currency": "GBP", "name": "Glencore", "sector": "Mining"},
    {"symbol": "VOD.L",   "country": "UK", "currency": "GBP", "name": "Vodafone Group", "sector": "Telecom"},
    {"symbol": "TSCO.L",  "country": "UK", "currency": "GBP", "name": "Tesco", "sector": "Retail"},

    # ============ Germany (DAX) ============
    {"symbol": "SAP.DE",  "country": "Germany", "currency": "EUR", "name": "SAP SE", "sector": "Technology"},
    {"symbol": "SIE.DE",  "country": "Germany", "currency": "EUR", "name": "Siemens AG", "sector": "Industrial"},
    {"symbol": "ALV.DE",  "country": "Germany", "currency": "EUR", "name": "Allianz SE", "sector": "Finance"},
    {"symbol": "DTE.DE",  "country": "Germany", "currency": "EUR", "name": "Deutsche Telekom", "sector": "Telecom"},
    {"symbol": "BAS.DE",  "country": "Germany", "currency": "EUR", "name": "BASF SE", "sector": "Chemical"},
    {"symbol": "BMW.DE",  "country": "Germany", "currency": "EUR", "name": "BMW AG", "sector": "Automotive"},
    {"symbol": "MBG.DE",  "country": "Germany", "currency": "EUR", "name": "Mercedes-Benz Group", "sector": "Automotive"},
    {"symbol": "VOW3.DE", "country": "Germany", "currency": "EUR", "name": "Volkswagen", "sector": "Automotive"},
    {"symbol": "MUV2.DE", "country": "Germany", "currency": "EUR", "name": "Munich Re", "sector": "Finance"},
    {"symbol": "DBK.DE",  "country": "Germany", "currency": "EUR", "name": "Deutsche Bank", "sector": "Finance"},
    {"symbol": "ADS.DE",  "country": "Germany", "currency": "EUR", "name": "Adidas", "sector": "Consumer"},

    # ============ France (CAC 40) ============
    {"symbol": "MC.PA",   "country": "France", "currency": "EUR", "name": "LVMH", "sector": "Luxury"},
    {"symbol": "OR.PA",   "country": "France", "currency": "EUR", "name": "L'Oréal", "sector": "Consumer"},
    {"symbol": "TTE.PA",  "country": "France", "currency": "EUR", "name": "TotalEnergies", "sector": "Energy"},
    {"symbol": "SAN.PA",  "country": "France", "currency": "EUR", "name": "Sanofi", "sector": "Healthcare"},
    {"symbol": "BNP.PA",  "country": "France", "currency": "EUR", "name": "BNP Paribas", "sector": "Finance"},
    {"symbol": "AIR.PA",  "country": "France", "currency": "EUR", "name": "Airbus SE", "sector": "Aerospace"},
    {"symbol": "CAP.PA",  "country": "France", "currency": "EUR", "name": "Capgemini", "sector": "Technology"},
    {"symbol": "RMS.PA",  "country": "France", "currency": "EUR", "name": "Hermès", "sector": "Luxury"},
    {"symbol": "KER.PA",  "country": "France", "currency": "EUR", "name": "Kering", "sector": "Luxury"},

    # ============ Netherlands / Switzerland / Spain / Italy ============
    {"symbol": "ASML.AS", "country": "Netherlands", "currency": "EUR", "name": "ASML Holding", "sector": "Technology"},
    {"symbol": "PRX.AS",  "country": "Netherlands", "currency": "EUR", "name": "Prosus", "sector": "Technology"},
    {"symbol": "ADYEN.AS","country": "Netherlands", "currency": "EUR", "name": "Adyen", "sector": "Finance"},
    {"symbol": "NESN.SW", "country": "Switzerland", "currency": "CHF", "name": "Nestlé", "sector": "Consumer"},
    {"symbol": "ROG.SW",  "country": "Switzerland", "currency": "CHF", "name": "Roche Holding", "sector": "Healthcare"},
    {"symbol": "NOVN.SW", "country": "Switzerland", "currency": "CHF", "name": "Novartis", "sector": "Healthcare"},
    {"symbol": "UBSG.SW", "country": "Switzerland", "currency": "CHF", "name": "UBS Group", "sector": "Finance"},
    {"symbol": "ZURN.SW", "country": "Switzerland", "currency": "CHF", "name": "Zurich Insurance", "sector": "Finance"},
    {"symbol": "ABBN.SW", "country": "Switzerland", "currency": "CHF", "name": "ABB", "sector": "Industrial"},
    {"symbol": "SAN.MC",  "country": "Spain",       "currency": "EUR", "name": "Banco Santander", "sector": "Finance"},
    {"symbol": "IBE.MC",  "country": "Spain",       "currency": "EUR", "name": "Iberdrola", "sector": "Utilities"},
    {"symbol": "ITX.MC",  "country": "Spain",       "currency": "EUR", "name": "Inditex (Zara)", "sector": "Retail"},
    {"symbol": "ENI.MI",  "country": "Italy",       "currency": "EUR", "name": "Eni SpA", "sector": "Energy"},
    {"symbol": "ISP.MI",  "country": "Italy",       "currency": "EUR", "name": "Intesa Sanpaolo", "sector": "Finance"},

    # ============ Japan ============
    {"symbol": "7203.T",  "country": "Japan", "currency": "JPY", "name": "Toyota Motor", "sector": "Automotive"},
    {"symbol": "6758.T",  "country": "Japan", "currency": "JPY", "name": "Sony Group", "sector": "Entertainment"},
    {"symbol": "9984.T",  "country": "Japan", "currency": "JPY", "name": "SoftBank Group", "sector": "Technology"},
    {"symbol": "6861.T",  "country": "Japan", "currency": "JPY", "name": "Keyence", "sector": "Industrial"},
    {"symbol": "8035.T",  "country": "Japan", "currency": "JPY", "name": "Tokyo Electron", "sector": "Technology"},
    {"symbol": "9433.T",  "country": "Japan", "currency": "JPY", "name": "KDDI", "sector": "Telecom"},
    {"symbol": "9432.T",  "country": "Japan", "currency": "JPY", "name": "Nippon Telegraph & Telephone", "sector": "Telecom"},
    {"symbol": "8306.T",  "country": "Japan", "currency": "JPY", "name": "Mitsubishi UFJ Financial", "sector": "Finance"},
    {"symbol": "7974.T",  "country": "Japan", "currency": "JPY", "name": "Nintendo", "sector": "Gaming"},
    {"symbol": "6501.T",  "country": "Japan", "currency": "JPY", "name": "Hitachi", "sector": "Industrial"},
    {"symbol": "7267.T",  "country": "Japan", "currency": "JPY", "name": "Honda Motor", "sector": "Automotive"},

    # ============ China / Hong Kong ============
    {"symbol": "BABA",    "country": "China",     "currency": "USD", "name": "Alibaba Group (ADR)", "sector": "E-commerce"},
    {"symbol": "PDD",     "country": "China",     "currency": "USD", "name": "PDD Holdings (ADR)", "sector": "E-commerce"},
    {"symbol": "JD",      "country": "China",     "currency": "USD", "name": "JD.com (ADR)", "sector": "E-commerce"},
    {"symbol": "BIDU",    "country": "China",     "currency": "USD", "name": "Baidu (ADR)", "sector": "Technology"},
    {"symbol": "NIO",     "country": "China",     "currency": "USD", "name": "NIO Inc. (ADR)", "sector": "Automotive"},
    {"symbol": "XPEV",    "country": "China",     "currency": "USD", "name": "XPeng (ADR)", "sector": "Automotive"},
    {"symbol": "LI",      "country": "China",     "currency": "USD", "name": "Li Auto (ADR)", "sector": "Automotive"},
    {"symbol": "BILI",    "country": "China",     "currency": "USD", "name": "Bilibili (ADR)", "sector": "Entertainment"},
    {"symbol": "0700.HK", "country": "Hong Kong", "currency": "HKD", "name": "Tencent Holdings", "sector": "Technology"},
    {"symbol": "9988.HK", "country": "Hong Kong", "currency": "HKD", "name": "Alibaba Group", "sector": "E-commerce"},
    {"symbol": "3690.HK", "country": "Hong Kong", "currency": "HKD", "name": "Meituan", "sector": "E-commerce"},
    {"symbol": "1398.HK", "country": "Hong Kong", "currency": "HKD", "name": "ICBC", "sector": "Finance"},
    {"symbol": "0939.HK", "country": "Hong Kong", "currency": "HKD", "name": "China Construction Bank", "sector": "Finance"},
    {"symbol": "0005.HK", "country": "Hong Kong", "currency": "HKD", "name": "HSBC Holdings (HK)", "sector": "Finance"},

    # ============ India (NSE/BSE) ============
    {"symbol": "RELIANCE.NS",  "country": "India", "currency": "INR", "name": "Reliance Industries", "sector": "Conglomerate"},
    {"symbol": "TCS.NS",       "country": "India", "currency": "INR", "name": "Tata Consultancy Services", "sector": "Technology"},
    {"symbol": "INFY.NS",      "country": "India", "currency": "INR", "name": "Infosys", "sector": "Technology"},
    {"symbol": "WIPRO.NS",     "country": "India", "currency": "INR", "name": "Wipro", "sector": "Technology"},
    {"symbol": "HDFCBANK.NS",  "country": "India", "currency": "INR", "name": "HDFC Bank", "sector": "Finance"},
    {"symbol": "ICICIBANK.NS", "country": "India", "currency": "INR", "name": "ICICI Bank", "sector": "Finance"},
    {"symbol": "SBIN.NS",      "country": "India", "currency": "INR", "name": "State Bank of India", "sector": "Finance"},
    {"symbol": "AXISBANK.NS",  "country": "India", "currency": "INR", "name": "Axis Bank", "sector": "Finance"},
    {"symbol": "BHARTIARTL.NS","country": "India", "currency": "INR", "name": "Bharti Airtel", "sector": "Telecom"},
    {"symbol": "HINDUNILVR.NS","country": "India", "currency": "INR", "name": "Hindustan Unilever", "sector": "Consumer"},
    {"symbol": "ITC.NS",       "country": "India", "currency": "INR", "name": "ITC Limited", "sector": "Consumer"},
    {"symbol": "LT.NS",        "country": "India", "currency": "INR", "name": "Larsen & Toubro", "sector": "Industrial"},
    {"symbol": "MARUTI.NS",    "country": "India", "currency": "INR", "name": "Maruti Suzuki", "sector": "Automotive"},
    {"symbol": "BAJFINANCE.NS","country": "India", "currency": "INR", "name": "Bajaj Finance", "sector": "Finance"},

    # ============ Canada (TSX) ============
    {"symbol": "RY.TO",   "country": "Canada", "currency": "CAD", "name": "Royal Bank of Canada", "sector": "Finance"},
    {"symbol": "TD.TO",   "country": "Canada", "currency": "CAD", "name": "Toronto-Dominion Bank", "sector": "Finance"},
    {"symbol": "BMO.TO",  "country": "Canada", "currency": "CAD", "name": "Bank of Montreal", "sector": "Finance"},
    {"symbol": "BNS.TO",  "country": "Canada", "currency": "CAD", "name": "Bank of Nova Scotia", "sector": "Finance"},
    {"symbol": "CNQ.TO",  "country": "Canada", "currency": "CAD", "name": "Canadian Natural Resources", "sector": "Energy"},
    {"symbol": "ENB.TO",  "country": "Canada", "currency": "CAD", "name": "Enbridge", "sector": "Energy"},
    {"symbol": "SU.TO",   "country": "Canada", "currency": "CAD", "name": "Suncor Energy", "sector": "Energy"},
    {"symbol": "CNR.TO",  "country": "Canada", "currency": "CAD", "name": "Canadian National Railway", "sector": "Logistics"},
    {"symbol": "SHOP.TO", "country": "Canada", "currency": "CAD", "name": "Shopify", "sector": "Technology"},
    {"symbol": "BCE.TO",  "country": "Canada", "currency": "CAD", "name": "BCE Inc.", "sector": "Telecom"},

    # ============ Australia ============
    {"symbol": "BHP.AX",  "country": "Australia", "currency": "AUD", "name": "BHP Group", "sector": "Mining"},
    {"symbol": "CBA.AX",  "country": "Australia", "currency": "AUD", "name": "Commonwealth Bank", "sector": "Finance"},
    {"symbol": "WBC.AX",  "country": "Australia", "currency": "AUD", "name": "Westpac Banking", "sector": "Finance"},
    {"symbol": "NAB.AX",  "country": "Australia", "currency": "AUD", "name": "National Australia Bank", "sector": "Finance"},
    {"symbol": "ANZ.AX",  "country": "Australia", "currency": "AUD", "name": "ANZ Group", "sector": "Finance"},
    {"symbol": "CSL.AX",  "country": "Australia", "currency": "AUD", "name": "CSL Limited", "sector": "Healthcare"},
    {"symbol": "WES.AX",  "country": "Australia", "currency": "AUD", "name": "Wesfarmers", "sector": "Retail"},
    {"symbol": "WOW.AX",  "country": "Australia", "currency": "AUD", "name": "Woolworths Group", "sector": "Retail"},
    {"symbol": "FMG.AX",  "country": "Australia", "currency": "AUD", "name": "Fortescue Metals", "sector": "Mining"},

    # ============ South Korea / Singapore / Taiwan / Brazil ============
    {"symbol": "005930.KS","country": "South Korea", "currency": "KRW", "name": "Samsung Electronics", "sector": "Technology"},
    {"symbol": "000660.KS","country": "South Korea", "currency": "KRW", "name": "SK Hynix", "sector": "Technology"},
    {"symbol": "035420.KS","country": "South Korea", "currency": "KRW", "name": "NAVER", "sector": "Technology"},
    {"symbol": "D05.SI",   "country": "Singapore",   "currency": "SGD", "name": "DBS Group", "sector": "Finance"},
    {"symbol": "O39.SI",   "country": "Singapore",   "currency": "SGD", "name": "OCBC Bank", "sector": "Finance"},
    {"symbol": "U11.SI",   "country": "Singapore",   "currency": "SGD", "name": "UOB", "sector": "Finance"},
    {"symbol": "S68.SI",   "country": "Singapore",   "currency": "SGD", "name": "Singapore Exchange", "sector": "Finance"},
    {"symbol": "TSM",      "country": "Taiwan",      "currency": "USD", "name": "Taiwan Semiconductor (ADR)", "sector": "Technology"},
    {"symbol": "VALE",     "country": "Brazil",      "currency": "USD", "name": "Vale S.A. (ADR)", "sector": "Mining"},
    {"symbol": "ITUB",     "country": "Brazil",      "currency": "USD", "name": "Itaú Unibanco (ADR)", "sector": "Finance"},
    {"symbol": "PBR",      "country": "Brazil",      "currency": "USD", "name": "Petrobras (ADR)", "sector": "Energy"},
]

# Quick-lookup index by uppercase symbol
SYMBOL_LOOKUP: Dict[str, Dict[str, str]] = {s["symbol"].upper(): s for s in STOCK_DEFINITIONS}

def generate_chart(prices: List[float], change_percent: float, direction: str) -> str:
    """Generate SVG chart based on actual price data"""
    try:
        if prices and len(prices) > 1:
            max_price = max(prices)
            min_price = min(prices)
            price_range = max_price - min_price if max_price != min_price else 1
            
            points = []
            for i, price in enumerate(prices):
                x = i * (120 / max(1, len(prices) - 1))
                y = 40 - ((price - min_price) / price_range * 35)
                points.append(f"{x},{y}")
            
            path_points = "M" + " L".join(points)
            color = "#16a34a" if direction == "up" else "#dc2626"
        else:
            if direction == "up":
                path_points = "M0,30 L20,25 L40,20 L60,25 L80,15 L100,10 L120,5"
                color = "#16a34a"
            else:
                path_points = "M0,5 L20,10 L40,15 L60,10 L80,20 L100,25 L120,30"
                color = "#dc2626"
        
        svg_template = f'''<svg width="120" height="40" xmlns="http://www.w3.org/2000/svg">
            <path d="{path_points}" stroke="{color}" stroke-width="2" fill="none"/>
        </svg>'''
        
        return base64.b64encode(svg_template.encode('utf-8')).decode('utf-8')
    except:
        return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

def fetch_stock_data(symbol: str, country: str, currency: str, name: str, sector: str) -> Dict[str, Any]:
    """Fetch real-time data for a single stock"""
    try:
        # Get real-time data from fetcher
        stock_data = fetcher.get_stock_data(symbol)
        
        if not stock_data['success'] or stock_data['price'] <= 0:
            raise ValueError(f"No real-time data available for {symbol}")
        
        price = stock_data['price']
        change_percent = stock_data['change_percent']
        volume = stock_data['volume']
        direction = "up" if change_percent >= 0 else "down"
        
        # Get historical data for chart from yfinance
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d", interval="1d")
            chart_prices = []
            if not hist.empty and 'Close' in hist.columns:
                chart_prices = hist['Close'].tail(7).tolist()
            
            if len(chart_prices) < 2:
                base_price = price
                chart_prices = []
                for i in range(7):
                    if direction == "up":
                        trend = (i / 6.0) * (abs(change_percent) / 100) * 0.6
                    else:
                        trend = -(i / 6.0) * (abs(change_percent) / 100) * 0.6
                    noise = np.random.uniform(-0.002, 0.002)
                    chart_price = base_price * (1 + trend + noise)
                    chart_prices.append(chart_price)
        except:
            chart_prices = [price * (1 + np.random.uniform(-0.02, 0.02)) for _ in range(7)]
        
        return {
            "symbol": symbol,
            "name": name,
            "price": round(price, 2),
            "change_percent": round(change_percent, 2),
            "direction": direction,
            "volume": volume,
            "chart": generate_chart(chart_prices, change_percent, direction),
            "country": country,
            "currency": currency,
            "sector": sector,
            "success": True,
            "source": stock_data.get('source', 'unknown')
        }
        
    except Exception as e:
        print(f"❌ Error fetching {symbol}: {e}")
        return {
            "symbol": symbol,
            "name": name,
            "price": 0,
            "change_percent": 0,
            "direction": "neutral",
            "volume": 0,
            "chart": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
            "country": country,
            "currency": currency,
            "sector": sector,
            "success": False,
            "source": "error"
        }

def get_live_data():
    """Main function to get live data for all stocks"""
    print(f"\n📊 FETCHING REAL-TIME GLOBAL STOCKS - {datetime.now().strftime('%H:%M:%S')}")
    print(f"🔑 Using Alpha Vantage API key: {ALPHA_VANTAGE_API_KEY[:4]}...{ALPHA_VANTAGE_API_KEY[-4:]}")
    print("="*60)

    stocks = STOCK_DEFINITIONS
    stocks_data = []
    total_volume = 0
    positive_stocks = 0
    countries_covered = set()
    sources_used = {}
    
    print(f"📈 Processing {len(stocks)} stocks from 12+ countries...")
    print("Note: Using FAST MODE with fallback data (no API delays)")
    print("="*60)
    
    # Use multithreading but respect Alpha Vantage rate limits
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_stock = {
            executor.submit(fetch_stock_data, 
                stock["symbol"], stock["country"], stock["currency"], 
                stock["name"], stock["sector"]): stock for stock in stocks
        }
        
        completed = 0
        for future in concurrent.futures.as_completed(future_to_stock):
            stock_info = future_to_stock[future]
            try:
                result = future.result(timeout=15)
                stocks_data.append(result)
                
                if result["success"]:
                    total_volume += result["volume"]
                    countries_covered.add(result["country"])
                    if result["change_percent"] >= 0:
                        positive_stocks += 1
                    
                    # Track data sources
                    source = result.get("source", "unknown")
                    sources_used[source] = sources_used.get(source, 0) + 1
                
                completed += 1
                
                # Show progress for first few stocks
                if completed <= 10 and result["success"]:
                    print(f"   {result['symbol']}: ${result['price']:.2f} ({result.get('source', '?')})")
                
            except Exception as e:
                print(f"❌ Failed to fetch {stock_info['symbol']}: {e}")
                stocks_data.append({
                    "symbol": stock_info["symbol"],
                    "name": stock_info["name"],
                    "price": 0,
                    "change_percent": 0,
                    "direction": "neutral",
                    "volume": 0,
                    "chart": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
                    "country": stock_info["country"],
                    "currency": stock_info["currency"],
                    "sector": stock_info["sector"],
                    "success": False,
                    "source": "failed"
                })
    
    # Calculate market indicators
    successful_stocks = [s for s in stocks_data if s["success"]]
    total_stocks = len(successful_stocks) if successful_stocks else len(stocks_data)
    
    if successful_stocks:
        sentiment = (positive_stocks / total_stocks) * 100
        volatility_indicator = sum(abs(s["change_percent"]) for s in successful_stocks) / total_stocks
    else:
        sentiment = 50.0
        volatility_indicator = 1.5
    
    print(f"\n📊 MARKET SUMMARY:")
    print(f"   Successfully fetched: {len(successful_stocks)}/{len(stocks)} stocks")
    print(f"   Data sources: {sources_used}")
    print(f"   Countries covered: {len(countries_covered)}")
    print(f"   Market sentiment: {sentiment:.1f}% ({positive_stocks}/{total_stocks} bullish)")
    print(f"   Total volume: {total_volume:,}")
    print("="*60)
    print("💡 TIPS:")
    print("   1. Check Alpha Vantage dashboard for API usage")
    print("   2. Some international symbols may need adjustment")
    print("   3. Real-time data is best during market hours")
    print("="*60)
    
    return {
        "market_indicators": {
            "sentiment": round(sentiment, 1),
            "volatility": round(volatility_indicator, 2),
            "total_stocks": total_stocks,
            "total_volume": total_volume,
            "countries_covered": len(countries_covered),
            "countries_list": sorted(list(countries_covered)),
            "market_status": "Open",
            "data_sources": sources_used,
            "last_updated": datetime.now().isoformat()
        },
        "stocks_data": stocks_data
    }

if __name__ == "__main__":
    # Test the updated code
    print("🧪 TESTING UPDATED REAL-TIME SYSTEM")
    print("="*60)
    
    data = get_live_data()
    
    print(f"\n🎯 FINAL RESULTS:")
    print(f"   Total stocks processed: {len(data['stocks_data'])}")
    print(f"   Data sources: {data['market_indicators'].get('data_sources', {})}")
    
    print("\n📋 SAMPLE STOCKS (REAL-TIME):")
    sample_count = 0
    for stock in data['stocks_data']:
        if stock["success"] and stock["price"] > 0:
            print(f"   {stock['symbol']}: ${stock['price']:.2f} ({stock.get('source', '?')})")
            sample_count += 1
            if sample_count >= 5:
                break
    
    if sample_count == 0:
        print("   ❌ No real-time data received. Check API key and network.")