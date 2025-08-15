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
import datetime
from enhanced_chatbot import IRISTradingChatbot

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
    return "🚀 IRIS Crypto Trading API - Welcome to the future of trading!", 200

@app.route("/api/predict", methods=["POST"])
def predict():
    """Enhanced prediction endpoint with better error handling"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON data provided"}), 400
            
        symbol = data.get("symbol", "ALL").upper()
        timeframe = data.get("timeframe", "hourly")

        # Validate timeframe
        valid_timeframes = ["hourly", "daily", "monthly"]
        if timeframe not in valid_timeframes:
            return jsonify({"error": f"Invalid timeframe. Supported: {valid_timeframes}"}), 400

        coin_mapping = {
            "BTC": ("Bitcoin", "bitcoin"),
            "ETH": ("Ethereum", "ethereum"),
            "BNB": ("Binance Coin", "binancecoin"),
            "ADA": ("Cardano", "cardano"),
            "SOL": ("Solana", "solana")
        }

        if symbol == "ALL":
            # Predict for all coins
            predictions = []
            for sym, (coin, coin_id) in coin_mapping.items():
                try:
                    result = predict_price(coin, coin_id, timeframe)
                    if result:
                        predictions.append({
                            "symbol": sym,
                            "current_price": result["current_price"],
                            "predicted_price_range": {
                                "low": result["predicted_price_range"][0],
                                "high": result["predicted_price_range"][1]
                            },
                            "market_pattern": result.get("market_pattern", "Unknown"),
                            "timeframe": result.get("timeframe", timeframe),
                            "potential_gain_percent": result.get("potential_gain_percent", 0),
                            "potential_loss_percent": result.get("potential_loss_percent", 0)
                        })
                    else:
                        predictions.append({
                            "symbol": sym,
                            "error": f"Failed to generate prediction for {coin}"
                        })
                except Exception as coin_error:
                    app.logger.error(f"Error predicting {sym}: {str(coin_error)}")
                    predictions.append({
                        "symbol": sym,
                        "error": f"Prediction failed for {coin}"
                    })
            
            return jsonify({"predictions": predictions})
        else:
            # Predict for a single coin
            if symbol not in coin_mapping:
                return jsonify({
                    "error": f"Unsupported symbol: {symbol}. Supported symbols: {list(coin_mapping.keys())}"
                }), 400

            coin, coin_id = coin_mapping[symbol]
            result = predict_price(coin, coin_id, timeframe)
            
            if not result:
                return jsonify({
                    "error": f"Failed to generate prediction for {coin} due to data fetching issues."
                }), 500

            response = {
                "symbol": symbol,
                "current_price": result["current_price"],
                "predicted_price": {
                    "low": result["predicted_price_range"][0],
                    "high": result["predicted_price_range"][1]
                },
                "market_pattern": result.get("market_pattern", "Unknown"),
                "timeframe": result.get("timeframe", timeframe),
                "horizon": result.get("horizon", "Next period"),
                "potential_gain_percent": result.get("potential_gain_percent", 0),
                "potential_loss_percent": result.get("potential_loss_percent", 0)
            }
            return jsonify(response)
            
    except Exception as e:
        app.logger.error(f"Prediction error: {str(e)}")
        return jsonify({"error": "Error generating prediction. Please try again."}), 500

@app.route("/api/predictions", methods=["GET"])
def get_predictions():
    """Fixed predictions endpoint with proper null checking"""
    conn = None
    cursor = None
    
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
        
        # Fix: Check if cursor.description exists before using it
        if cursor.description is not None:
            columns = [desc[0] for desc in cursor.description]
            predictions = [dict(zip(columns, row)) for row in rows]
        else:
            # Fallback: Return empty predictions if no description
            predictions = []
            app.logger.warning("No cursor description available - empty result set")
        
        return jsonify({
            "predictions": predictions,
            "count": len(predictions),
            "status": "success"
        })
        
    except psycopg2.Error as db_error:
        app.logger.error(f"Database connection error: {str(db_error)}")
        return jsonify({
            "error": "Database connection failed. Please check your database configuration.",
            "status": "database_error"
        }), 500
    except Exception as e:
        app.logger.error(f"Database query error: {str(e)}")
        return jsonify({
            "error": "Error fetching predictions from database.",
            "status": "query_error"
        }), 500
    finally:
        # Ensure proper cleanup
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route("/api/trade", methods=["POST"])
def trade():
    """Enhanced trading endpoint with better validation"""
    try:
        # Validate request data
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON data provided"}), 400
            
        symbol = data.get("symbol", "BTCUSDT").upper()  # e.g., BTCUSDT
        quantity = data.get("quantity")
        side = data.get("side", "").upper()  # BUY or SELL
        api_key = data.get("api_key")
        secret_key = data.get("secret_key")

        # Validate inputs
        if not all([symbol, quantity, side, api_key, secret_key]):
            return jsonify({
                "error": "Missing required fields: symbol, quantity, side, api_key, secret_key"
            }), 400
            
        if side not in ["BUY", "SELL"]:
            return jsonify({"error": "Invalid side: must be 'BUY' or 'SELL'"}), 400
            
        try:
            quantity = float(quantity)
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid quantity: must be a positive number"}), 400

        # Validate symbol format (basic check)
        if not symbol.endswith('USDT') and not symbol.endswith('BUSD'):
            app.logger.warning(f"Unusual trading pair: {symbol}")

        # Initialize Binance client and execute trade
        client = Client(api_key, secret_key)

        # Test connection first
        try:
            account_info = client.get_account()
            app.logger.info(f"Binance connection successful for trade: {symbol}")
        except Exception as conn_error:
            return jsonify({
                "error": "Failed to connect to Binance. Please check your API credentials."
            }), 401

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
            "symbol": order["symbol"],
            "side": order["side"],
            "quantity": order["executedQty"],
            "price": order.get("price", "Market Price"),
            "message": f"Successfully placed {side} order for {quantity} {symbol}",
            "timestamp": order["transactTime"]
        })
        
    except Exception as e:
        app.logger.error(f"Binance trade error: {str(e)}")
        error_msg = str(e)
        
        # Provide more specific error messages
        if "Invalid symbol" in error_msg:
            return jsonify({"error": f"Invalid trading symbol: {symbol}"}), 400
        elif "Insufficient balance" in error_msg:
            return jsonify({"error": "Insufficient balance for this trade"}), 400
        elif "API-key format invalid" in error_msg:
            return jsonify({"error": "Invalid API key format"}), 401
        else:
            return jsonify({"error": f"Failed to execute trade: {error_msg}"}), 500

@app.route("/api/chat", methods=["POST"])
def chat():
    """Enhanced chat endpoint for IRIS trading website"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "reply": "Invalid request format. Please send a message.",
                "type": "error"
            }), 400
            
        user_message = data.get("message", "").strip()
        
        if not user_message:
            return jsonify({
                "reply": "How can I help you with crypto trading today?",
                "type": "welcome"
            }), 400
        
        # Rate limiting check (basic)
        if len(user_message) > 500:
            return jsonify({
                "reply": "Message too long. Please keep it under 500 characters.",
                "type": "error"
            }), 400
        
        # Initialize enhanced chatbot
        chatbot = IRISTradingChatbot(openai_client, newsapi_key, config)
        
        # Generate response using new chatbot
        response = chatbot.generate_response(user_message)
        
        # Log successful chat interaction
        app.logger.info(f"Chat interaction - Intent: {response.get('type', 'unknown')}")
        
        return jsonify(response)
        
    except Exception as e:
        app.logger.error(f"Chatbot error: {str(e)}")
        return jsonify({
            "reply": "🤖 I'm experiencing technical difficulties. Please try asking about crypto prices, market news, or trading advice.",
            "type": "error"
        }), 500

@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        conn = psycopg2.connect(database_url)
        conn.close()
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    return jsonify({
        "status": "healthy",
        "service": "IRIS Crypto Trading API",
        "database": db_status,
        "timestamp": datetime.datetime.now() if db_status == "connected" else None
    })

@app.route("/api/status", methods=["GET"])
def api_status():
    """API status and supported features"""
    return jsonify({
        "api_name": "IRIS Crypto Trading API",
        "version": "2.0",
        "supported_coins": ["BTC", "ETH", "BNB", "ADA", "SOL"],
        "features": {
            "price_prediction": True,
            "live_trading": True,
            "ai_chatbot": True,
            "market_news": True,
            "technical_analysis": True
        },
        "endpoints": {
            "predict": "/api/predict",
            "trade": "/api/trade", 
            "chat": "/api/chat",
            "predictions": "/api/predictions",
            "health": "/api/health"
        }
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint not found",
        "message": "Please check the API documentation at /swagger"
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal server error",
        "message": "Something went wrong. Please try again later."
    }), 500

@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        "error": "Bad request",
        "message": "Please check your request format and try again."
    }), 400

if __name__ == "__main__":
    app.run(debug=True, port=5001, host='0.0.0.0')
