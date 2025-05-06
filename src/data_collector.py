# # src/data_collector.py
# import requests
# import json
# from datetime import datetime, timedelta

# class DataCollector:
#     def __init__(self, config):
#         self.config = config
#         self.headers = {"x-cg-api-key": self.config.get("coingecko_api_key", "")} if self.config.get("coingecko_api_key") else {}

#     def get_current_price(self, coin_id):
#         url = f"{self.config['coingecko_api_url']}?ids={coin_id}&vs_currencies=usd"
#         try:
#             response = requests.get(url, headers=self.headers, timeout=10)
#             response.raise_for_status()
#             return response.json()[coin_id]["usd"]
#         except requests.RequestException as e:
#             print(f"Error fetching price for {coin_id}: {e}")
#             return None

#     def get_crypto_news(self, query):
#         url = f"{self.config['newsapi_url']}?q={query}&from={datetime.now().date()}&sortBy=publishedAt&apiKey={self.config['newsapi_key']}"
#         try:
#             response = requests.get(url, timeout=10)
#             response.raise_for_status()
#             articles = response.json()["articles"][:5]
#             return [f"{a['title']}: {a['description']}" for a in articles]
#         except requests.RequestException as e:
#             print(f"Error fetching news for {query}: {e}")
#             return []

#     def get_major_events(self, coin):
#         # Static events, could be expanded per coin
#         return {
#             "bitcoin": ["Elon Musk tweet: BTC is the future, April 2, 2025", "VanEck ETF filing news, March 31, 2025"],
#             "ethereum": ["Ethereum upgrade news, March 2025", "DeFi adoption spike, April 1, 2025"],
#             "binancecoin": ["Binance expansion news, March 2025", "BNB staking update, April 3, 2025"],
#             "cardano": ["Cardano smart contract milestone, March 2025", "ADA ecosystem growth, April 2, 2025"],
#             "solana": ["Solana scalability upgrade, March 2025", "SOL DeFi surge, April 1, 2025"]
#         }.get(coin.lower(), [])

#     def get_historical_data(self, coin_id, timeframe="daily", periods=60):
#         if timeframe == "hourly":
#             days = periods / 24
#             url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days={days}&interval=hourly"
#         elif timeframe == "daily":
#             url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days={periods}&interval=daily"
#         elif timeframe == "monthly":
#             days = periods * 30
#             url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days={days}&interval=daily"
#         else:
#             raise ValueError("Timeframe must be 'hourly', 'daily', or 'monthly'")
#         try:
#             response = requests.get(url, headers=self.headers, timeout=10)
#             response.raise_for_status()
#             data = response.json()
#             prices = [p[1] for p in data["prices"][-periods:]]
#             volumes = [v[1] for v in data["total_volumes"][-periods:]]
#             return prices, volumes
#         except requests.RequestException as e:
#             print(f"Error fetching historical data for {coin_id}: {e}")
#             return None, None


# src/data_collector.py
from binance.client import Client
import requests

class DataCollector:
    def __init__(self, config):
        self.config = config
        # Initialize Binance client (no API key needed for public endpoints)
        self.binance_client = Client()

    def get_current_price_and_trend(self, coin_id):
        # Map CoinGecko coin_id to Binance symbol
        symbol_mapping = {
            "bitcoin": "BTCUSDT",
            "ethereum": "ETHUSDT",
            "binancecoin": "BNBUSDT",
            "cardano": "ADAUSDT",
            "solana": "SOLUSDT"
        }
        symbol = symbol_mapping.get(coin_id)
        if not symbol:
            raise ValueError(f"Unsupported coin_id: {coin_id}")

        try:
            # Fetch ticker data from Binance
            ticker = self.binance_client.get_symbol_ticker(symbol=symbol)
            current_price = float(ticker["price"])

            # Fetch 24-hour ticker data for price change percentage
            ticker_24h = self.binance_client.get_ticker(symbol=symbol)
            price_change_percent = float(ticker_24h["priceChangePercent"])

            return current_price, price_change_percent
        except Exception as e:
            raise Exception(f"Failed to fetch price data from Binance: {str(e)}")

    # Keep get_current_price for compatibility, but it now uses the new method
    def get_current_price(self, coin_id):
        current_price, _ = self.get_current_price_and_trend(coin_id)
        return current_price