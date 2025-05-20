# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import requests
import os
import psycopg2
from dotenv import load_dotenv
from binance.client import Client
from src.utils import load_config
from main import predict_price
from flask_swagger_ui import get_swaggerui_blueprint

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests from frontend

### swagger specific ###
SWAGGER_URL = '/swagger'
API_URL = '/static/swagger.yml'
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "Crypto Trading API"
    }
)
app.register_blueprint(swaggerui_blueprint)
### end swagger specific ###

# Load environment variables (for NewsAPI key)
load_dotenv()
newsapi_key = os.getenv("NEWSAPI_KEY")

# Load config and get database URL and OpenAI API key
config = load_config("config.json")
database_url = config.get("database_url")
if not database_url:
    raise ValueError("database_url not found in config.json")

openai_api_key = config.get("openai_api_key")
if not openai_api_key:
    raise ValueError("openai_api_key not found in config.json")

# Initialize OpenAI client
openai_client = OpenAI(api_key=openai_api_key)

@app.route("/", methods=["GET"])
def init():
    return "Hii welcome", 200

@app.route("/api/predict", methods=["POST"])
def predict():
    data = request.get_json()
    symbol = data.get("symbol", "ALL").upper()
    timeframe = data.get("timeframe", "hourly")

    coin_mapping = {
        "BTC": ("Bitcoin", "bitcoin"),
        "ETH": ("Ethereum", "ethereum"),
        "BNB": ("Binance Coin", "binancecoin"),
        "ADA": ("Cardano", "cardano"),
        "SOL": ("Solana", "solana")
    }

    try:
        if symbol == "ALL":
            # Predict for all coins
            predictions = []
            for sym, (coin, coin_id) in coin_mapping.items():
                result = predict_price(coin, coin_id, timeframe)
                if result:
                    predictions.append({
                        # "coin": result["coin"],
                        "symbol": sym,
                        "current_price": result["current_price"],
                        "predicted_price_range": {
                            "low": result["predicted_price_range"][0],
                            "high": result["predicted_price_range"][1]
                        },
                        # "market_pattern": result["market_pattern"],
                        # "timeframe": result["timeframe"],
                        # "horizon": result["horizon"],
                        # "potential_gain_percent": result["potential_gain_percent"],
                        # "potential_loss_percent": result["potential_loss_percent"]
                    })
                else:
                    predictions.append({
                        "coin": coin,
                        "symbol": sym,
                        "error": f"Failed to generate prediction for {coin}"
                    })
            return jsonify({"predictions": predictions})
        else:
            # Predict for a single coin
            if symbol not in coin_mapping:
                return jsonify({"error": f"Unsupported symbol: {symbol}. Supported symbols: {list(coin_mapping.keys())}"}), 400

            coin, coin_id = coin_mapping[symbol]
            result = predict_price(coin, coin_id, timeframe)
            if not result:
                return jsonify({"error": f"Failed to generate prediction for {coin} due to data fetching issues."}), 500

            response = {
                # "coin": result["coin"],
                "symbol": symbol,
                "current_price": result["current_price"],
                "predicted_price": {
                    "low": result["predicted_price_range"][0],
                    "high": result["predicted_price_range"][1]
                },
                # "market_pattern": result["market_pattern"],
                # "timeframe": result["timeframe"],
                # "horizon": result["horizon"],
                # "potential_gain_percent": result["potential_gain_percent"],
                # "potential_loss_percent": result["potential_loss_percent"]
            }
            return jsonify(response)
    except Exception as e:
        app.logger.error(f"Prediction error: {str(e)}")
        return jsonify({"error": "Error generating prediction. Please try again."}), 500

@app.route("/api/predictions", methods=["GET"])
def get_predictions():
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        # Fetch the latest prediction for each coin
        query = """
            SELECT * FROM price_predictions
            WHERE recorded_at = (
                SELECT MAX(recorded_at)
                FROM price_predictions
                WHERE coin = price_predictions.coin
            )
            ORDER BY recorded_at DESC
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        predictions = [dict(zip(columns, row)) for row in rows]
        conn.close()
        return jsonify({"predictions": predictions})
    except Exception as e:
        app.logger.error(f"Database query error: {str(e)}")
        return jsonify({"error": "Error fetching predictions from database."}), 500

@app.route("/api/trade", methods=["POST"])
def trade():
    # Validate request
    data = request.get_json()
    symbol = data.get("symbol", "BTCUSDT").upper()  # e.g., BTCUSDT
    quantity = data.get("quantity")
    side = data.get("side").upper()  # BUY or SELL
    api_key = data.get("api_key")
    secret_key = data.get("secret_key")

    # Validate inputs
    if not all([symbol, quantity, side, api_key, secret_key]):
        return jsonify({"error": "Missing required fields: symbol, quantity, side, api_key, secret_key"}), 400
    if side not in ["BUY", "SELL"]:
        return jsonify({"error": "Invalid side: must be 'BUY' or 'SELL'"}), 400
    try:
        quantity = float(quantity)
        if quantity <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid quantity: must be a positive number"}), 400

    try:
        # Initialize Binance client
        client = Client(api_key, secret_key)

        # Place a market order
        order = client.create_order(
            symbol=symbol,
            side=side,
            type=Client.ORDER_TYPE_MARKET,
            quantity=quantity
        )

        return jsonify({
            "order_id": order["orderId"],
            "status": order["status"],
            "message": f"Successfully placed {side} order for {quantity} {symbol}"
        })
    except Exception as e:
        app.logger.error(f"Binance trade error: {str(e)}")
        return jsonify({"error": f"Failed to execute trade: {str(e)}"}), 500

@app.route("/api/chat", methods=["POST"])
def chat():
    # Validate request
    data = request.get_json()
    user_message = data.get("message")
    if not user_message or not isinstance(user_message, str):
        return jsonify({"reply": "Invalid or missing message."}), 400

    try:
        # Check if user is asking for news
        if "news" in user_message.lower():
            # Fetch market news from NewsAPI
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": "cryptocurrency OR stock market",
                "apiKey": newsapi_key,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 5,
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            articles = response.json().get("articles", [])
            if not articles:
                reply = "No recent market news found."
            else:
                news_summary = "\n".join(
                    f"- {article['title']} ({article['source']['name']})"
                    for article in articles
                )
                reply = f"Recent market news:\n{news_summary}\n\nSource: NewsAPI"
        else:
            # Check if the message is asking for a trade suggestion or prediction
            symbol = None
            if "crypto should I buy" in user_message.lower() or "what to buy" in user_message.lower():
                # Extract symbol if provided, default to BTC
                symbol = "BTC"
                # Call ML prediction endpoint internally
                prediction_response = requests.post("http://localhost:5000/api/predict", json={"symbol": symbol, "timeframe": "hourly"})
                prediction_response.raise_for_status()
                prediction_data = prediction_response.json()
                if "error" in prediction_data:
                    prediction_text = prediction_data["error"]
                else:
                    prediction_text = (
                        f"Price Prediction for {prediction_data['coin']} ({prediction_data['timeframe']}):\n"
                        f"- Current Price: ${prediction_data['current_price']:,.2f}\n"
                        f"- Predicted Price Range: ${prediction_data['predicted_price_range']['low']:,.2f} - ${prediction_data['predicted_price_range']['high']:,.2f}\n"
                        f"- Market Pattern: {prediction_data['market_pattern']}\n"
                        f"- Potential Gain: {prediction_data['potential_gain_percent']:.2f}%\n"
                        f"- Potential Loss: {prediction_data['potential_loss_percent']:.2f}%"
                    )
            else:
                prediction_text = ""

            # Use OpenAI for trade suggestions
            completion = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a financial assistant. Provide general trade suggestions based on market trends, "
                            "focusing on cryptocurrencies and stocks. Avoid specific price predictions or guarantees. "
                            "Keep responses concise, professional, and under 150 words. Always append this disclaimer: "
                            "'This is not financial advice. Consult a professional before making investment decisions.'"
                        ),
                    },
                    {"role": "user", "content": user_message},
                ],
                max_tokens=150,
                temperature=0.7,
            )
            openai_reply = completion.choices[0].message.content.strip()
            # Combine OpenAI response with price prediction if applicable
            reply = f"{openai_reply}\n\n{prediction_text if prediction_text else ''}"
            # Ensure disclaimer is included
            if "not financial advice" not in reply.lower():
                reply += "\n\nDisclaimer: This is not financial advice. Consult a professional before making investment decisions."

        return jsonify({"reply": reply})

    except requests.RequestException as e:
        app.logger.error(f"NewsAPI error: {str(e)}")
        return jsonify({"reply": "Error fetching news. Please try again later."}), 500
    except Exception as e:
        app.logger.error(f"OpenAI or general error: {str(e)}")
        return jsonify({"reply": "Error processing request. Please try again."}), 500

# if __name__ == "__main__":
#     app.run(debug=True, port=5000)
