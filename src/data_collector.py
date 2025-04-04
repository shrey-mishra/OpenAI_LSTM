# src/data_collector.py
import requests
import json
from datetime import datetime, timedelta

class DataCollector:
    def __init__(self, config):
        self.config = config
        self.headers = {"x-cg-api-key": self.config.get("coingecko_api_key", "")} if self.config.get("coingecko_api_key") else {}

    def get_current_price(self, coin_id="bitcoin"):
        url = f"{self.config['coingecko_api_url']}?ids={coin_id}&vs_currencies=usd"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()[coin_id]["usd"]
        except requests.RequestException as e:
            print(f"Error fetching price: {e}")
            return None

    def get_crypto_news(self, query="Bitcoin"):
        url = f"{self.config['newsapi_url']}?q={query}&from={datetime.now().date()}&sortBy=publishedAt&apiKey={self.config['newsapi_key']}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            articles = response.json()["articles"][:5]
            return [f"{a['title']}: {a['description']}" for a in articles]
        except requests.RequestException as e:
            print(f"Error fetching news: {e}")
            return []

    def get_major_events(self):
        return [
            "Elon Musk tweet: BTC is the future, April 2, 2025",
            "VanEck ETF filing news, March 31, 2025"
        ]

    def get_historical_data(self, coin_id="bitcoin", timeframe="daily", periods=60):
        if timeframe == "hourly":
            days = periods / 24
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days={days}&interval=hourly"
        elif timeframe == "daily":
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days={periods}&interval=daily"
        elif timeframe == "monthly":
            days = periods * 30
            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days={days}&interval=daily"
        else:
            raise ValueError("Timeframe must be 'hourly', 'daily', or 'monthly'")
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            prices = [p[1] for p in data["prices"][-periods:]]
            volumes = [v[1] for v in data["total_volumes"][-periods:]]
            return prices, volumes
        except requests.RequestException as e:
            print(f"Error fetching historical data: {e}")
            return None, None