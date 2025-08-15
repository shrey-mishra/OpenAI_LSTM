# enhanced_chatbot.py
# Enhanced Trading Chatbot for IRIS Website

import re
import requests
from datetime import datetime
import spacy
from textblob import TextBlob

class IRISTradingChatbot:
    def __init__(self, openai_client, newsapi_key, config):
        self.openai_client = openai_client
        self.newsapi_key = newsapi_key
        self.config = config
        
        # Load spaCy model for NLP (install: python -m spacy download en_core_web_sm)
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            self.nlp = None
            print("Warning: spaCy model not found. Install with: python -m spacy download en_core_web_sm")
            
        # Supported cryptocurrencies
        self.supported_coins = {
            'bitcoin': ['btc', 'bitcoin'],
            'ethereum': ['eth', 'ethereum', 'ether'],
            'binancecoin': ['bnb', 'binance coin', 'binance'],
            'cardano': ['ada', 'cardano'],
            'solana': ['sol', 'solana'],
            'ripple': ['xrp', 'ripple'],
            'dogecoin': ['doge', 'dogecoin'],
            'polygon': ['matic', 'polygon'],
            'chainlink': ['link', 'chainlink'],
            'avalanche-2': ['avax', 'avalanche']
        }
        
        # Trading-related keywords
        self.trading_keywords = [
            'buy', 'sell', 'trade', 'trading', 'investment', 'invest', 'portfolio',
            'price', 'market', 'crypto', 'cryptocurrency', 'bitcoin', 'ethereum',
            'profit', 'loss', 'gain', 'bullish', 'bearish', 'analysis',
            'prediction', 'forecast', 'trend', 'technical', 'fundamental',
            'support', 'resistance', 'volume', 'chart', 'candle', 'pump', 'dump',
            'hodl', 'moon', 'dip', 'rally', 'correction', 'breakout'
        ]

    def is_trading_related(self, message):
        """Check if message is trading-related using NLP"""
        message_lower = message.lower()
        
        # Check for direct trading keywords
        if any(keyword in message_lower for keyword in self.trading_keywords):
            return True
            
        # Check for coin mentions
        if any(coin in message_lower for coins in self.supported_coins.values() for coin in coins):
            return True
            
        # Use spaCy for entity recognition if available
        if self.nlp:
            doc = self.nlp(message)
            for ent in doc.ents:
                if ent.label_ in ['MONEY', 'PERCENT', 'ORG'] and any(keyword in ent.text.lower() for keyword in self.trading_keywords):
                    return True
        
        return False

    def extract_coin_from_message(self, message):
        """Extract cryptocurrency from user message"""
        message_lower = message.lower()
        
        for coin_id, aliases in self.supported_coins.items():
            for alias in aliases:
                if alias in message_lower:
                    return coin_id, alias.upper()
        return None, None

    def get_live_price(self, coin_id):
        """Fetch live price from CoinGecko API"""
        try:
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd&include_24hr_change=true"
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if coin_id in data:
                price = data[coin_id]['usd']
                change_24h = data[coin_id].get('usd_24h_change', 0)
                return price, change_24h
            return None, None
        except Exception as e:
            print(f"Error fetching price for {coin_id}: {e}")
            return None, None

    def get_market_news(self, limit=3):
        """Fetch latest crypto market news via CoinDesk Data API (fallback from NewsAPI)."""
        try:
            # Prefer config-provided URL/API key; otherwise default to public CoinDesk endpoint
            base_url = self.config.get(
                "coindesk_news_url",
                "https://data-api.coindesk.com/news/v1/article/list"
            )
            coindesk_api_key = self.config.get("coindesk_api_key")

            # Constrain limit within API bounds
            effective_limit = max(1, min(int(limit or 3), 10))

            params = {
                "lang": "EN",
                "limit": effective_limit,
            }
            if coindesk_api_key:
                params["api_key"] = coindesk_api_key

            response = requests.get(base_url, params=params, timeout=7)
            response.raise_for_status()
            data = response.json()

            # CoinDesk returns articles under "Data"
            items = data.get("Data") or data.get("data") or []

            normalized = []
            for item in items[:effective_limit]:
                title = item.get("TITLE") or item.get("title") or "Untitled"
                url = item.get("URL") or item.get("url")
                source_data = item.get("SOURCE_DATA") or {}
                source_name = source_data.get("NAME") or source_data.get("name") or "CoinDesk"
                normalized.append({
                    "title": title,
                    "url": url,
                    # Keep shape compatible with existing renderer: article['source']['name']
                    "source": {"name": source_name},
                })

            return normalized
        except Exception as e:
            print(f"Error fetching news: {e}")
            return []

    def _summarize_news(self, articles):
        """Return a single concise summary of the news list.
        Tries OpenAI first; falls back to heuristic summarization.
        """
        try:
            # Build a compact context from titles and sources
            bullet_points = []
            for a in articles:
                title = a.get("title") or ""
                source = (a.get("source") or {}).get("name") or ""
                if title:
                    bullet_points.append(f"- {title} ({source})")

            if bullet_points and getattr(self, 'openai_client', None):
                prompt = (
                    "You are a crypto market editor. Summarize the following headlines into one brief, cohesive "
                    "market wrap (2-3 sentences, no bullets, no markdown). Focus on what matters for traders: "
                    "themes, risks, and opportunities.\n\n" + "\n".join(bullet_points)
                )
                try:
                    completion = self.openai_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "You produce concise, trader-focused market wraps without hype."
                                ),
                            },
                            {"role": "user", "content": prompt},
                        ],
                        max_tokens=140,
                        temperature=0.2,
                    )
                    text = completion.choices[0].message.content.strip()
                    if text:
                        return text
                except Exception:
                    # Fall back if the model call fails
                    pass

            # Heuristic fallback: compress titles and add quick sentiment cue
            titles = [a.get("title") for a in articles if a.get("title")]
            joined = "; ".join(titles[:5])
            polarity = 0.0
            if joined:
                try:
                    polarity = TextBlob(joined).sentiment.polarity
                except Exception:
                    polarity = 0.0
            sentiment = "mixed"
            if polarity > 0.1:
                sentiment = "slightly positive"
            elif polarity < -0.1:
                sentiment = "slightly negative"
            if joined:
                return f"Market wrap ({sentiment}): {joined}."
            return "Market wrap: No notable headlines available right now."
        except Exception:
            return "Market wrap: Unable to summarize news at the moment."

    def classify_intent(self, message):
        """Classify user intent using NLP"""
        message_lower = message.lower()
        
        # Price inquiry patterns
        price_patterns = [
            r'price of (\w+)', r'(\w+) price', r'current (\w+)',
            r'how much is (\w+)', r'(\w+) cost', r'(\w+) worth',
            r'what.*(\w+).*trading', r'(\w+).*value'
        ]
        
        # News inquiry patterns
        news_patterns = [
            r'news', r'latest', r'updates', r'happening', r'market.*today'
        ]
        
        # Trading advice patterns
        advice_patterns = [
            r'should i buy', r'should i sell', r'what to buy',
            r'trading advice', r'investment advice', r'recommend',
            r'good time to', r'worth buying', r'worth selling'
        ]
        
        # Prediction patterns
        prediction_patterns = [
            r'predict', r'forecast', r'future', r'trend', r'analysis',
            r'going up', r'going down', r'will.*rise', r'will.*fall'
        ]

        if any(re.search(pattern, message_lower) for pattern in price_patterns):
            return "price_inquiry"
        elif any(re.search(pattern, message_lower) for pattern in news_patterns):
            return "news_inquiry"
        elif any(re.search(pattern, message_lower) for pattern in advice_patterns):
            return "trading_advice"
        elif any(re.search(pattern, message_lower) for pattern in prediction_patterns):
            return "prediction_request"
        else:
            return "general"

    def generate_response(self, message):
        """Generate chatbot response"""
        # Check if message is trading-related
        if not self.is_trading_related(message):
            return {
                "reply": "I'm IRIS, your crypto trading assistant. I can help with cryptocurrency prices, market analysis, trading advice, and market news. How can I assist you with trading today?",
                "type": "off_topic"
            }

        # Classify user intent
        intent = self.classify_intent(message)
        
        try:
            if intent == "price_inquiry":
                return self.handle_price_inquiry(message)
            elif intent == "news_inquiry":
                return self.handle_news_inquiry()
            elif intent == "trading_advice":
                return self.handle_trading_advice(message)
            elif intent == "prediction_request":
                return self.handle_prediction_request(message)
            else:
                return self.handle_general_query(message)
                
        except Exception as e:
            print(f"Error generating response: {e}")
            return {
                "reply": "I'm experiencing technical difficulties. Please try again or ask about crypto prices, market news, or trading advice.",
                "type": "error"
            }

    def handle_price_inquiry(self, message):
        """Handle price-related queries"""
        coin_id, coin_symbol = self.extract_coin_from_message(message)
        
        if not coin_id:
            return {
                "reply": "📊 Which cryptocurrency price would you like to know? I support BTC, ETH, BNB, ADA, SOL, XRP, DOGE, MATIC, LINK, and AVAX.",
                "type": "price_clarification"
            }
        
        price, change_24h = self.get_live_price(coin_id)
        
        if price is None:
            return {
                "reply": f"❌ Unable to fetch live price for {coin_symbol}. Please try again.",
                "type": "price_error"
            }
        # Format price response
        if change_24h is not None:
            change_emoji = "📈" if change_24h > 0 else "📉" if change_24h < 0 else "➡️"
        else:
            change_emoji = "➡️"

        response = f"💰 **{coin_symbol}** Live Price\n"
        response += f"💵 ${price:,.2f} USD\n"
        response += f"{change_emoji} 24h Change: {change_24h:+.2f}%\n"
        response += f"🕐 Updated: {datetime.now().strftime('%H:%M UTC')}"
        
        return {
            "reply": response,
            "type": "price_response",
            "data": {
                "coin": coin_symbol,
                "price": price,
                "change_24h": change_24h
            }
        }

    def handle_news_inquiry(self):
        """Handle news-related queries"""
        articles = self.get_market_news(5)
        if not articles:
            return {"reply": "📰 Market wrap: News feed unavailable right now.", "type": "news_error"}

        summary = self._summarize_news(articles)
        return {"reply": f"📰 {summary}", "type": "news_response"}

    def handle_trading_advice(self, message):
        """Handle trading advice queries with OpenAI"""
        coin_id, coin_symbol = self.extract_coin_from_message(message)
        
        # Get current price if coin is mentioned
        price_context = ""
        if coin_id:
            price, change_24h = self.get_live_price(coin_id)
            if price:
                price_context = f"Current {coin_symbol} price: ${price:,.2f} (24h: {change_24h:+.2f}%)"
        
        try:
            # Create focused prompt for trading advice
            system_prompt = """You are IRIS, a professional crypto trading assistant. Provide concise, actionable trading insights.

Rules:
- Keep responses under 100 words
- Focus on technical analysis and market trends
- Include risk warnings
- No financial advice disclaimers in every response
- Be direct and professional
- Use bullet points for clarity"""

            user_prompt = f"{message}\n\nContext: {price_context}" if price_context else message
            
            completion = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=120,
                temperature=0.3
            )
            
            ai_response = completion.choices[0].message.content.strip()
            
            # Add price context if available
            if price_context:
                response = f"📊 {price_context}\n\n{ai_response}"
            else:
                response = ai_response
            
            # Add brief risk note
            response += "\n\n⚠️ Trade responsibly. Markets are volatile."
            
            return {
                "reply": response,
                "type": "trading_advice"
            }
            
        except Exception:
            # Fallback advice using simple heuristics
            fallback_lines = []
            if coin_id:
                price, change_24h = self.get_live_price(coin_id)
            else:
                price, change_24h = None, None

            if price:
                fallback_lines.append(f"📊 Current {coin_symbol} ~ ${price:,.2f}{' (' + ('+' if change_24h and change_24h>0 else '') + f'{change_24h:.2f}%' + ')' if change_24h is not None else ''}")

            if change_24h is not None:
                if change_24h > 1:
                    # Up-trend
                    fallback_lines.extend([
                        "• Trend: short-term bullish; consider scaling in on pullbacks.",
                        "• Risk: set a tight stop below recent support; risk ≤1–2% per trade.",
                        "• Confirm with volume and RSI before entry."
                    ])
                elif change_24h < -1:
                    # Down-trend
                    fallback_lines.extend([
                        "• Trend: short-term bearish; avoid chasing dips.",
                        "• Plan: wait for a base or use small DCA; if trading, use tight stops.",
                        "• Watch key support/resistance for reversal signals."
                    ])
                else:
                    # Range-bound
                    fallback_lines.extend([
                        "• Trend: range-bound; momentum unclear.",
                        "• Plan: wait for breakout/confirmation; keep position size small.",
                        "• Use bracket orders (stop + take-profit) to manage risk."
                    ])
            else:
                # No change data
                fallback_lines.extend([
                    "• Data limited; consider waiting for clearer momentum.",
                    "• If entering, use a tight stop and small size."
                ])

            fallback_lines.append("⚠️ Volatility can spike; adjust stops and size accordingly.")
            return {
                "reply": "\n".join(fallback_lines),
                "type": "trading_advice"
            }

    def handle_prediction_request(self, message):
        """Handle prediction requests"""
        coin_id, coin_symbol = self.extract_coin_from_message(message)
        
        if not coin_symbol:
            return {
                "reply": "📈 Which cryptocurrency would you like a prediction for? (BTC, ETH, BNB, ADA, SOL, etc.)",
                "type": "prediction_clarification"
            }
        
        try:
            # Call internal prediction API (prefer configured base_url, default to port 5001)
            base_url = self.config.get('base_url') or 'http://localhost:5001'
            prediction_url = f"{base_url}/api/predict"
            response = requests.post(
                prediction_url,
                json={"symbol": coin_symbol, "timeframe": "hourly"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                current_price = data.get('current_price', 0)
                pred_low = data.get('predicted_price', {}).get('low', 0)
                pred_high = data.get('predicted_price', {}).get('high', 0)
                
                response_text = f"🔮 **{coin_symbol} Prediction (Next Hour)**\n"
                response_text += f"💰 Current: ${current_price:,.2f}\n"
                response_text += f"📊 Predicted Range: ${pred_low:,.2f} - ${pred_high:,.2f}\n"
                response_text += f"📈 Potential: {((pred_high - current_price) / current_price * 100):+.1f}%\n"
                response_text += "\n⚡ Based on technical analysis"
                
                return {
                    "reply": response_text,
                    "type": "prediction_response",
                    "data": data
                }
            else:
                return {
                    "reply": f"📊 Prediction service unavailable for {coin_symbol}. Try asking for current price instead.",
                    "type": "prediction_error"
                }
                
        except Exception as e:
            return {
                "reply": f"🔮 Prediction analysis in progress for {coin_symbol}. Meanwhile, I can provide current price and market news.",
                "type": "prediction_error"
            }

    def handle_general_query(self, message):
        """Handle general trading queries"""
        try:
            completion = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are IRIS, a crypto trading assistant. Answer briefly (under 80 words). Focus on trading, market analysis, or crypto education. Stay professional and concise."
                    },
                    {"role": "user", "content": message}
                ],
                max_tokens=100,
                temperature=0.4
            )
            
            response = completion.choices[0].message.content.strip()
            
            return {
                "reply": response,
                "type": "general_response"
            }
            
        except Exception as e:
            return {
                "reply": "🤖 I'm here to help with crypto trading. Ask me about coin prices, market analysis, or trading strategies!",
                "type": "general_fallback"
            }
