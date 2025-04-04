# src/grok_analyzer.py
import requests
import json
from typing import Dict, Optional
from textblob import TextBlob
import logging

class GrokAnalyzer:
    def __init__(self, config):
        self.config = config
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config['openai_api_key']}"
        }
        self.url = self.config["openai_api_url"]
        logging.basicConfig(level=logging.INFO)

    def analyze_trends(self, coin: str, current_price: float, news: list, events: list) -> Optional[Dict]:
        prompt = self._build_prompt(coin, current_price, news, events)
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are Grok, a super smart crypto analyst with expertise in sentiment analysis and price prediction."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0
        }
        try:
            response = requests.post(self.url, headers=self.headers, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()["choices"][0]["message"]["content"]
            logging.info(f"OpenAI Response: {result}")
            return self._parse_response(result)
        except requests.RequestException as e:
            logging.error(f"API Error: {e.response.text if e.response else e}")
            return self._simulate_grok_response(coin, current_price, news, events)

    def _build_prompt(self, coin: str, current_price: float, news: list, events: list) -> str:
        news_str = "\n- ".join(news)
        events_str = "\n- ".join(events)
        return (
            f"Analyze the following for {coin}:\n"
            f"- Current Price: ${current_price}\n"
            f"- Trending News:\n- {news_str}\n"
            f"- Major Events:\n- {events_str}\n"
            "Output in this format (use ' - ' with spaces for the range):\n"
            "- Current Price: [value]\n"
            "- Predicted Price Range: [low] - [high]\n"
            "- Pattern: [bearish/bullish/mixed]"
        )

    def _parse_response(self, response: str) -> Dict:
        logging.info(f"Parsing response: {response}")
        lines = response.strip().split("\n")
        result = {}
        for line in lines:
            if "Current Price" in line:
                result["current_price"] = float(line.split(": $")[1].replace(",", ""))
            elif "Predicted Price Range" in line:
                range_str = line.split(": ")[1]
                try:
                    # Handle both " - " and "-" formats
                    if " - " in range_str:
                        low, high = range_str.split(" - ")
                    elif "-" in range_str:
                        low, high = range_str.split("-")
                    else:
                        raise ValueError("No valid separator found")
                    result["price_range"] = (float(low.replace("$", "").replace(",", "")),
                                            float(high.replace("$", "").replace(",", "")))
                except ValueError as e:
                    logging.error(f"Invalid range format: {range_str}, Error: {e}")
                    # Fallback: Use current price ±2% if range parsing fails
                    single_value = result.get("current_price", current_price)
                    result["price_range"] = (single_value * 0.98, single_value * 1.02)
            elif "Pattern" in line:
                result["pattern"] = line.split(": ")[1]
        return result

    def _simulate_grok_response(self, coin: str, current_price: float, news: list, events: list) -> Dict:
        text = " ".join(news + events).lower()
        sentiment = TextBlob(text).sentiment.polarity
        if sentiment > 0.2:
            pattern = "bullish"
            volatility = 0.03
        elif sentiment < -0.2:
            pattern = "bearish"
            volatility = 0.03
        else:
            pattern = "mixed"
            volatility = 0.02
        if "recession" in text or "crash" in text:
            range_low = current_price * (1 - volatility * 1.5)
            range_high = current_price * (1 + volatility * 0.5)
        elif "elon" in text or "etf" in text:
            range_low = current_price * (1 - volatility * 0.5)
            range_high = current_price * (1 + volatility * 1.5)
        else:
            range_low = current_price * (1 - volatility)
            range_high = current_price * (1 + volatility)
        return {
            "current_price": current_price,
            "price_range": (range_low, range_high),
            "pattern": pattern
        }