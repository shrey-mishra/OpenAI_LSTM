# # main.py
# from src.data_collector import DataCollector
# from src.grok_analyzer import GrokAnalyzer
# from src.utils import load_config, setup_logging

# def run_door1(coin="Bitcoin"):
#     logger = setup_logging()
#     config = load_config("config.json")
    
#     # Step 1: Collect data
#     collector = DataCollector(config)
#     current_price = collector.get_current_price("bitcoin")
#     news = collector.get_crypto_news(coin)
#     events = collector.get_major_events()

#     if current_price is None:
#         logger.error("Failed to fetch current price. Exiting.")
#         return

#     # Step 2: Analyze with Grok
#     analyzer = GrokAnalyzer(config)
#     result = analyzer.analyze_trends(coin, current_price, news, events)

#     # Step 3: Display results
#     logger.info(f"Door I Results for {coin}:")
#     logger.info(f"- Current Price: ${result['current_price']:,.2f}")
#     logger.info(f"- Predicted Price Range: ${result['price_range'][0]:,.2f} - ${result['price_range'][1]:,.2f}")
#     logger.info(f"- Pattern: {result['pattern']}")

# if __name__ == "__main__":
#     run_door1("Bitcoin")

# main.py
from src.data_collector import DataCollector
from src.grok_analyzer import GrokAnalyzer
from lstm_predictor import LSTMPredictor
from src.utils import load_config, setup_logging

def run_door1(coin="Bitcoin"):
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
    result = analyzer.analyze_trends(coin, current_price, news, events)
    logger.info(f"Door I Results for {coin}:")
    logger.info(f"- Current Price: ${result['current_price']:,.2f}")
    logger.info(f"- Predicted Price Range: ${result['price_range'][0]:,.2f} - ${result['price_range'][1]:,.2f}")
    logger.info(f"- Pattern: {result['pattern']}")
    return result, collector

if __name__ == "__main__":
    door1_result, collector = run_door1("Bitcoin")
    if door1_result:
        # Fetch historical data
        prices, volumes = collector.get_historical_data("bitcoin")
        if prices and volumes:
            # Dummy sentiments (replace with real analysis if available)
            sentiments = [0.5] * len(prices)  # Assume neutral/bullish
            lstm = LSTMPredictor()
            lstm.train(prices, volumes, sentiments)
            final_price = lstm.predict(
                door1_result["current_price"],
                13000,  # Placeholder volume
                0.5 if door1_result["pattern"] == "Bullish" else -0.5,
                door1_result["price_range"],
                door1_result["pattern"]
            )
            print(f"Door II Final Predicted Price: ${final_price:,.2f}")
        else:
            print("Failed to fetch historical data for Door II")