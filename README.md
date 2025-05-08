# OpenAI_LSTM

## Project Description

This project is a cryptocurrency trading API that uses OpenAI and LSTM models to predict cryptocurrency prices and provide trade suggestions.

## Features

*   Predicts cryptocurrency prices using OpenAI and LSTM models.
*   Provides trade suggestions based on market trends.
*   Executes trades on Binance.
*   Provides a chatbot interface for market news and trade suggestions.
*   Fetches market news from NewsAPI.
*   Uses CoinGecko API to get cryptocurrency prices.

## API Endpoints

*   `/api/predict`: Predicts cryptocurrency prices.
*   `/api/predictions`: Retrieves the latest price predictions from the database.
*   `/api/trade`: Executes a trade on Binance.
*   `/api/chat`: Provides a chatbot interface for market news and trade suggestions.

See the `API_README.md` file for more details on the API endpoints.

## Setup Instructions

1.  Clone the repository.
2.  Install the dependencies using `pip install -r requirements.txt`.
3.  Create a `config.json` file with the following structure:

```json
{
    "xai_api_url": "https://api.x.ai/v1/chat/completions",
    "xai_api_key": "AIzaSyCS8AhPLl96rvaWFPWUqppBxv8za0NQAZs",
    "coingecko_api_url": "https://api.coingecko.com/api/v3/simple/price",
    "newsapi_url": "https://newsapi.org/v2/everything",
    "newsapi_key": "8f92bd1029c84772a3b2de989648bdf9",
    "gemini_api_url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
    "gemini_api_key": "AIzaSyBgWfLISJdswkmj7bGUweQDsPjK4juOxnA",
    "openai_api_url": "https://api.openai.com/v1/chat/completions",
    "openai_api_key": "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",
    "coingecko_api_key": "CG-gm82WYZT7Jhy2HkDrgYpZRa9",
    "database_url": "postgresql://postgres:shreym7478@localhost/postgres"
}
```

4.  Set the environment variables for the NewsAPI key and Binance API keys.

## Usage

1.  Start the Flask application using `python app.py`.
2.  Access the API endpoints using a tool like Postman or curl.

## Starting the Flask Application

To start the flask application, run the following command:

```
python app.py
```

The application will run in debug mode on port 5000.
