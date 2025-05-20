# src/grok_analyzer.py
import requests
import json
from typing import Dict, Optional
from textblob import TextBlob
import logging
from datetime import datetime, timedelta

class GrokAnalyzer:
    def __init__(self, config):
        self.config = config
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config['openai_api_key']}"
        }
        self.url = self.config["openai_api_url"]
        logging.basicConfig(level=logging.INFO)

    def analyze_trends(self, coin: str, current_price: float, timeframe: str = "daily") -> Optional[Dict]:
        prompt = self._build_prompt(coin, current_price, timeframe)
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are Grok, a super smart crypto analyst with expertise in sentiment analysis and price prediction."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5
        }
        try:
            response = requests.post(self.url, headers=self.headers, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()["choices"][0]["message"]["content"]
            logging.info(f"OpenAI Response: {result}")
            return self._parse_response(result)
        except requests.RequestException as e:
            logging.error(f"API Error: {e.response.text if e.response else e}")
            return self._simulate_grok_response(coin, current_price, timeframe)

    def _build_prompt(self, coin: str, current_price: float, timeframe: str) -> str:
        if timeframe == "hourly":
            horizon = (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M')
            period = "next 1 hour"
            range_instruction = f"Predict a tight price range (±$500 from ${current_price})"
        elif timeframe == "daily":
            horizon = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d %H:%M')
            period = "next day"
            range_instruction = "Predict a price range"
        elif timeframe == "monthly":
            horizon = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d %H:%M')
            period = "next month"
            range_instruction = "Predict a price range"
        else:
            raise ValueError("Timeframe must be 'hourly', 'daily', or 'monthly'")
        
        return (
            f"Analyze the following for {coin}:\n"
            f"- Current Price: ${current_price}\n"
            f"{range_instruction} for the {period} (by {horizon}). "
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
                    single_value = result.get("current_price", current_price)
                    result["price_range"] = (single_value * 0.98, single_value * 1.02)
            elif "Pattern" in line:
                result["pattern"] = line.split(": ")[1]
        return result

    def _simulate_grok_response(self, coin: str, current_price: float, timeframe: str) -> Dict:
        sentiment = 0
        if sentiment > 0.2:
            pattern = "bullish"
            volatility = 0.01 if timeframe == "hourly" else 0.03 if timeframe == "monthly" else 0.02
        elif sentiment < -0.2:
            pattern = "bearish"
            volatility = 0.01 if timeframe == "hourly" else 0.03 if timeframe == "monthly" else 0.02
        else:
            pattern = "mixed"
            volatility = 0.005 if timeframe == "hourly" else 0.02 if timeframe == "monthly" else 0.015
        range_low = current_price * (1 - volatility)
        range_high = current_price * (1 + volatility)
        return {
            "current_price": current_price,
            "price_range": (range_low, range_high),
            "pattern": pattern
        }
