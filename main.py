# main.py
import argparse
from datetime import datetime, timedelta
from src.data_collector import DataCollector
from src.utils import load_config, setup_logging

def predict_price(coin="Bitcoin", coin_id="bitcoin", timeframe="hourly"):
    logger = setup_logging()
    config = load_config("config.json")
    collector = DataCollector(config)
    
    try:
        current_price, price_change_percent = collector.get_current_price_and_trend(coin_id)
    except Exception as e:
        logger.error(f"Failed to fetch price data for {coin}: {str(e)}")
        return None

    if price_change_percent > 1:
        pattern = "Bullish"
        predicted_low = current_price * 0.99
        predicted_high = current_price * 1.03
    elif price_change_percent < -1:
        pattern = "Bearish"
        predicted_low = current_price * 0.97
        predicted_high = current_price * 1.01
    else:
        pattern = "Mixed"
        predicted_low = current_price * 0.98
        predicted_high = current_price * 1.02

    predicted_price_range = (predicted_low, predicted_high)
    potential_gain = ((predicted_high - current_price) / current_price) * 100
    potential_loss = ((current_price - predicted_low) / current_price) * 100

    horizon = (datetime.now() + 
               (timedelta(hours=1) if timeframe == "hourly" 
                else timedelta(days=1) if timeframe == "daily" 
                else timedelta(days=30))).strftime('%Y-%m-%d %H:%M')

    result = {
        "coin": coin,
        "coin_id": coin_id,
        "current_price": current_price,
        "predicted_price_range": predicted_price_range,
        "market_pattern": pattern,
        "timeframe": timeframe,
        "horizon": horizon,
        "potential_gain_percent": potential_gain,
        "potential_loss_percent": potential_loss
    }

    logger.info(f"Price Prediction for {coin} ({timeframe} prediction, by {horizon}):")
    logger.info(f"- Current Price: ${current_price:,.2f}")
    logger.info(f"- Predicted Price Range: ${predicted_price_range[0]:,.2f} - ${predicted_price_range[1]:,.2f}")
    logger.info(f"- Market Pattern: {pattern}")
    logger.info(f"- Potential Gain: {potential_gain:.2f}%")
    logger.info(f"- Potential Loss: {potential_loss:.2f}%")

    return result

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

    for coin, coin_id in coins:
        result = predict_price(coin, coin_id, args.timeframe)
        if result:
            print(f"Price Prediction for {coin} ({args.timeframe}):")
            print(f"- Current Price: ${result['current_price']:,.2f}")
            print(f"- Predicted Price Range: ${result['predicted_price_range'][0]:,.2f} - ${result['predicted_price_range'][1]:,.2f}")
            print(f"- Market Pattern: {result['market_pattern']}")
            print(f"- Potential Gain: {result['potential_gain_percent']:.2f}%")
            print(f"- Potential Loss: {result['potential_loss_percent']:.2f}%")
            print("-" * 50)
        else:
            print(f"Failed to predict price for {coin}")
