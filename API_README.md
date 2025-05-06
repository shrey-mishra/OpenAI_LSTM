# Crypto Trading API Documentation

## /api/predict

**POST**

Predicts cryptocurrency prices.

**Request Body:**

```json
{
  "symbol": "string", // The cryptocurrency symbol (e.g., BTC, ETH, ALL)
  "timeframe": "string"  // The timeframe for the prediction (e.g., hourly, daily)
}
```

**Responses:**

-   200: Successful prediction
-   400: Invalid symbol
-   500: Prediction error

## /api/predictions

**GET**

Retrieves the latest price predictions from the database.

**Responses:**

-   200: Successful retrieval of predictions
-   500: Database query error

## /api/trade

**POST**

Executes a trade on Binance.

**Request Body:**

```json
{
  "symbol": "string",      // The trading symbol (e.g., BTCUSDT)
  "quantity": "number",    // The quantity to trade
  "side": "string",        // The side of the trade (BUY or SELL)
  "api_key": "string",     // Your Binance API key
  "secret_key": "string"   // Your Binance secret key
}
```

**Responses:**

-   200: Successful trade execution
-   400: Missing required fields or invalid side
-   500: Trade execution error

## /api/chat

**POST**

Provides a chatbot interface for market news and trade suggestions.

**Request Body:**

```json
{
  "message": "string"  // The user's message
}
```

**Responses:**

-   200: Successful chat response
-   400: Invalid or missing message
-   500: Error processing request
