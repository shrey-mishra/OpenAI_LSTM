# main.py
import argparse
from datetime import datetime, timedelta
import os
import psycopg2
from dotenv import load_dotenv
from src.data_collector import DataCollector
from src.utils import load_config, setup_logging

# Load environment variables
load_dotenv()

# Initialize PostgreSQL database
def init_db(database_url):
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_predictions (
                id SERIAL PRIMARY KEY,
                coin TEXT NOT NULL,
                coin_id TEXT NOT NULL,
                current_price DOUBLE PRECISION NOT NULL,
                predicted_price_low DOUBLE PRECISION NOT NULL,
                predicted_price_high DOUBLE PRECISION NOT NULL,
                market_pattern TEXT NOT NULL,
                potential_gain_percent DOUBLE PRECISION NOT NULL,
                potential_loss_percent DOUBLE PRECISION NOT NULL,
                timeframe TEXT NOT NULL,
                horizon TEXT NOT NULL,
                recorded_at TIMESTAMP NOT NULL
            )
        """)
        conn.commit()
        return conn
    except Exception as e:
        print(f"Failed to connect to database or create table: {str(e)}")
        raise

def store_prediction(conn, result):
    try:
        cursor = conn.cursor()
        recorded_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            INSERT INTO price_predictions (
                coin, coin_id, current_price, predicted_price_low, predicted_price_high,
                market_pattern, potential_gain_percent, potential_loss_percent,
                timeframe, horizon, recorded_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            result["coin"],
            result["coin_id"],
            result["current_price"],
            result["predicted_price_range"][0],
            result["predicted_price_range"][1],
            result["market_pattern"],
            result["potential_gain_percent"],
            result["potential_loss_percent"],
            result["timeframe"],
            result["horizon"],
            recorded_at
        ))
        conn.commit()
    except Exception as e:
        print(f"Failed to store prediction: {str(e)}")
        raise

def predict_price(coin="Bitcoin", coin_id="bitcoin", timeframe="hourly"):
    logger = setup_logging()
    config = load_config("config.json")
    collector = DataCollector(config)
    
    # Fetch current price and 24-hour price change percentage
    try:
        current_price, price_change_percent = collector.get_current_price_and_trend(coin_id)
    except Exception as e:
        logger.error(f"Failed to fetch price data for {coin}: {str(e)}")
        return None

    # Determine market pattern based on 24-hour price change
    if price_change_percent > 1:
        pattern = "Bullish"
        # Slightly adjust prediction range for Bullish pattern (more upside)
        predicted_low = current_price * 0.99  # -1%
        predicted_high = current_price * 1.03  # +3%
    elif price_change_percent < -1:
        pattern = "Bearish"
        # Slightly adjust prediction range for Bearish pattern (more downside)
        predicted_low = current_price * 0.97  # -3%
        predicted_high = current_price * 1.01  # +1%
    else:
        pattern = "Mixed"
        # Neutral prediction range
        predicted_low = current_price * 0.98  # -2%
        predicted_high = current_price * 1.02  # +2%

    predicted_price_range = (predicted_low, predicted_high)
    
    # Calculate potential gain/loss
    potential_gain = ((predicted_high - current_price) / current_price) * 100
    potential_loss = ((current_price - predicted_low) / current_price) * 100
    
    # Format the result
    horizon = (datetime.now() + (timedelta(hours=1) if timeframe == "hourly" else timedelta(days=1) if timeframe == "daily" else timedelta(days=30))).strftime('%Y-%m-%d %H:%M')
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
    
    # Log the result
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

    # Load config and get database URL
    config = load_config("config.json")
    database_url = config.get("database_url")
    if not database_url:
        print("Error: database_url not found in config.json")
        exit(1)

    # Initialize database
    conn = init_db(database_url)

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
            # Store the prediction in the database
            store_prediction(conn, result)
            # Print the prediction
            print(f"Price Prediction for {coin} ({args.timeframe}):")
            print(f"- Current Price: ${result['current_price']:,.2f}")
            print(f"- Predicted Price Range: ${result['predicted_price_range'][0]:,.2f} - ${result['predicted_price_range'][1]:,.2f}")
            print(f"- Market Pattern: {result['market_pattern']}")
            print("-" * 50)
        else:
            print(f"Failed to predict price for {coin}")

    # Close the database connection
    conn.close()