import numpy as np
import tensorflow as tf
from src.data_collector import DataCollector
from src.grok_analyzer import GrokAnalyzer
from src.lstm_predictor import LSTMPredictor
from src.utils import load_config, setup_logging
import argparse
import time
import pandas as pd
from datetime import datetime, timedelta
import os

def run_door1(coin="Bitcoin", coin_id="bitcoin", timeframe="hourly"):
    logger = setup_logging()
    config = load_config("config.json")
    collector = DataCollector(config)
    current_price = collector.get_current_price(coin_id)
    if current_price is None:
        logger.error(f"Failed to fetch current price for {coin}. Using fallback price.")
        current_price = 82748 if coin_id == "bitcoin" else 1782.35 if coin_id == "ethereum" else 589.75 if coin_id == "binancecoin" else 0.636597 if coin_id == "cardano" else 150.0
    analyzer = GrokAnalyzer(config)
    result = analyzer.analyze_trends(coin, current_price, timeframe)
    horizon = (datetime.now() + (timedelta(hours=1) if timeframe == "hourly" else timedelta(days=1) if timeframe == "daily" else timedelta(days=30))).strftime('%Y-%m-%d %H:%M')
    logger.info(f"Door I Target Range for {coin} ({timeframe} prediction, by {horizon}):")
    logger.info(f"- Current Price: ${result['current_price']:,.2f}")
    logger.info(f"- Predicted Target Range: ${result['price_range'][0]:,.2f} - ${result['price_range'][1]:,.2f}")
    logger.info(f"- Pattern: {result['pattern']}")
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

def save_data(coin, timestamp, current_price, door1_low, door1_high, door2_low, door2_high, pattern):
    data = {
        "timestamp": timestamp,
        "current_price": current_price,
        "door1_low": door1_low,
        "door1_high": door1_high,
        "door2_low": door2_low,
        "door2_high": door2_high,
        "pattern": pattern
    }
    df = pd.DataFrame([data])
    file_path = f"{coin.lower()}_data.csv"
    if os.path.exists(file_path):
        df.to_csv(file_path, mode='a', header=False, index=False)
    else:
        df.to_csv(file_path, mode='w', header=True, index=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crypto price prediction with timeframe")
    parser.add_argument("--timeframe", type=str, default="hourly", choices=["hourly", "daily", "monthly"], help="Prediction timeframe")
    args = parser.parse_args()

    coins = [
        ("Bitcoin", "bitcoin"),
        ("Ethereum", "ethereum"),
        ("Binance Coin", "binancecoin"),
        ("Cardano", "cardano"),
        ("Solana", "solana")
    ]

    np.random.seed(42)
    tf.random.set_seed(42)

    while True:
        for coin, coin_id in coins:
            door1_result, collector = run_door1(coin, coin_id, args.timeframe)
            if door1_result:
                try:
                    lstm = LSTMPredictor(args.timeframe)
                    narrow_low, narrow_high = lstm.predict(
                        door1_result["current_price"],
                        13000,
                        0.5 if door1_result["pattern"] == "Bullish" else -0.5 if door1_result["pattern"] == "Bearish" else 0,
                        door1_result["price_range"],
                        door1_result["pattern"]
                    )
                except Exception as e:
                    print(f"Warning: Using fallback narrowing for {coin} due to LSTM failure: {e}")
                    low, high = door1_result["price_range"]
                    mid = (low + high) / 2
                    range_width = 200 if coin_id in ["bitcoin", "ethereum", "binancecoin", "solana"] else 0.005
                    narrow_low = max(low, mid - range_width)
                    narrow_high = min(high, mid + range_width)
                
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"[{timestamp}] Door II Narrowed Range for {coin} ({args.timeframe}): ${narrow_low:,.2f} - ${narrow_high:,.2f}")
                print(recommend_trade(door1_result["current_price"], door1_result["price_range"], (narrow_low, narrow_high), door1_result["pattern"]))
                print("-" * 50)
                
                # Save data
                save_data(
                    coin,
                    timestamp,
                    door1_result["current_price"],
                    door1_result["price_range"][0],
                    door1_result["price_range"][1],
                    narrow_low,
                    narrow_high,
                    door1_result["pattern"]
                )
            else:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Failed to run Door I for {coin}")
        print("Waiting 300 seconds for next fetch...")
        time.sleep(300)
