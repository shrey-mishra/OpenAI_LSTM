# src/lstm_predictor.py
import pandas as pd
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
from sklearn.preprocessing import MinMaxScaler
import logging

class LSTMPredictor:
    def __init__(self):
        self.scaler = MinMaxScaler()
        self.model = self._build_model()
        self.is_trained = False

    def _build_model(self):
        model = Sequential()
        model.add(Input(shape=(60, 3)))  # Define input shape explicitly
        model.add(LSTM(50, return_sequences=False))
        model.add(Dropout(0.2))
        model.add(Dense(1))
        model.compile(optimizer='adam', loss='mse')
        return model

    def train(self, prices, volumes, sentiments):
        """Train the LSTM with historical data."""
        if len(prices) < 60:
            raise ValueError("Need at least 60 days of data")
        data = pd.DataFrame({'price': prices, 'volume': volumes, 'sentiment': sentiments})
        scaled_data = self.scaler.fit_transform(data)
        X = np.array([scaled_data[i-60:i] for i in range(60, len(scaled_data))])
        y = scaled_data[60:, 0]  # Next price
        self.model.fit(X, y, epochs=50, batch_size=32, verbose=1)
        self.is_trained = True
        logging.info("LSTM model trained successfully")

    def predict(self, current_price, volume, sentiment, door1_range, door1_pattern):
        """Predict final price using Door I's output."""
        if not self.is_trained:
            raise ValueError("Model must be trained before predicting")
        # Build a 60-timestep input with last row as current data
        data = np.zeros((60, 3))
        data[-1] = [current_price, volume, 0.5 if door1_pattern == "Bullish" else -0.5]
        scaled_data = self.scaler.transform(data)
        X = scaled_data.reshape((1, 60, 3))
        pred_scaled = self.model.predict(X, verbose=0)
        pred_price = self.scaler.inverse_transform([[pred_scaled[0][0], 0, 0]])[0][0]
        # Constrain within Door I range
        low, high = door1_range
        return max(low, min(high, pred_price))