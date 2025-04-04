# main.py
import numpy as np
import tensorflow as tf
from src.data_collector import DataCollector
from src.grok_analyzer import GrokAnalyzer
from src.lstm_predictor import LSTMPredictor
from src.utils import load_config, setup_logging
import argparse
from datetime import datetime, timedelta

def run_door1(coin="Bitcoin", timeframe="hourly"):
    logger = setup_logging()
    config = load_config("config.json")
    collector = DataCollector(config)
    current_price = collector.get_current_price("bitcoin")
    news = collector.get_crypto_news(coin)
    events = collector.get_major_events()
    if current_price is None:
        logger.error("Failed to fetch current price. Exiting.")
        return None
    analyzer = GrokAnalyzer(config)
    result = analyzer.analyze_trends(coin, current_price, news, events, timeframe)
    horizon = (datetime.now() + (timedelta(hours=1) if timeframe == "hourly" else timedelta(days=1) if timeframe == "daily" else timedelta(days=30))).strftime('%Y-%m-%d %H:%M')
    logger.info(f"Door I Target Range for {coin} ({timeframe} prediction, by {horizon}):")
    logger.info(f"- Current Price: ${result['current_price']:,.2f}")
    logger.info(f"- Predicted Target Range: ${result['price_range'][0]:,.2f} - ${result['price_range'][1]:,.2f}")
    logger.info(f"- Pattern: ${result['pattern']}")
    return result, collector

def recommend_trade(current_price, target_range, narrowed_range, pattern):
    low, high = target_range
    narrow_low, narrow_high = narrowed_range
    potential_gain = (narrow_high - current_price) / current_price * 100
    potential_loss = (current_price - narrow_low) / current_price * 100 if narrow_low < current_price else 0
    recommendation = (
        f"Trading Recommendation ({pattern} pattern):\n"
        f"- Current Price: ${current_price:,.2f}\n"
        f"- Door I Range: ${low:,.2f} - ${high:,.2f}\n"
        f"- Narrowed Range (Door II): ${narrow_low:,.2f} - ${narrow_high:,.2f}\n"
        f"- Potential Gain: {potential_gain:.2f}%\n"
        f"- Potential Loss: {potential_loss:.2f}%\n"
    )
    if pattern == "Bullish":
        recommendation += "- Action: Buy/Hold within narrowed range."
    elif pattern == "Bearish":
        recommendation += "- Action: Consider selling/shorting within narrowed range."
    else:
        recommendation += "- Action: Monitor within narrowed range."
    return recommendation

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crypto price prediction with timeframe")
    parser.add_argument("--timeframe", type=str, default="hourly", choices=["hourly", "daily", "monthly"], help="Prediction timeframe")
    args = parser.parse_args()

    np.random.seed(42)
    tf.random.set_seed(42)
    door1_result, collector = run_door1("Bitcoin", args.timeframe)
    if door1_result:
        periods = 60 if args.timeframe == "hourly" else 90 if args.timeframe == "daily" else 24
        prices, volumes = collector.get_historical_data("bitcoin", args.timeframe, periods)
        if prices and volumes:
            sentiments = [0.5] * len(prices)
            lstm = LSTMPredictor(args.timeframe)
            lstm.train(prices, volumes, sentiments)
            narrow_low, narrow_high = lstm.predict(
                door1_result["current_price"],
                13000,
                0.5 if door1_result["pattern"] == "Bullish" else -0.5 if door1_result["pattern"] == "Bearish" else 0,
                door1_result["price_range"],
                door1_result["pattern"]
            )
        else:
            # Fallback: Narrow Door I range by 40% (±$200)
            print("Warning: Using fallback narrowing due to CoinGecko API failure")
            low, high = door1_result["price_range"]
            mid = (low + high) / 2
            narrow_low = max(low, mid - 200)
            narrow_high = min(high, mid + 200)
        print(f"Door II Narrowed Range ({args.timeframe}): ${narrow_low:,.2f} - ${narrow_high:,.2f}")
        print(recommend_trade(door1_result["current_price"], door1_result["price_range"], (narrow_low, narrow_high), door1_result["pattern"]))
    else:
        print("Failed to run Door I")