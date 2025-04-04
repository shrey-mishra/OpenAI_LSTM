# src/lstm_predictor.py
import pandas as pd
import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
from sklearn.preprocessing import MinMaxScaler
import logging

class LSTMPredictor:
    def __init__(self, timeframe="daily"):
        self.scaler = MinMaxScaler()
        self.timeframe = timeframe
        self.window = 36 if timeframe == "hourly" else 60 if timeframe == "daily" else 12
        self.step = 24 if timeframe == "hourly" else 1 if timeframe == "daily" else 1
        self.model = self._build_model()
        self.is_trained = False
        self.last_data = None

    def _build_model(self):
        model = Sequential()
        model.add(Input(shape=(self.window, 3)))
        model.add(LSTM(50, return_sequences=False))
        model.add(Dropout(0.2))
        model.add(Dense(1))
        model.compile(optimizer='adam', loss='mse')
        return model

    def train(self, prices, volumes, sentiments):
        data = pd.DataFrame({'price': prices, 'volume': volumes, 'sentiment': sentiments})
        if len(data) < self.window + self.step:
            raise ValueError(f"Need at least {self.window + self.step} periods of data")
        scaled_data = self.scaler.fit_transform(data)
        X, y = [], []
        for i in range(self.window, len(scaled_data) - self.step + 1):
            X.append(scaled_data[i-self.window:i])
            y.append(scaled_data[i+self.step-1, 0])
        X = np.array(X)
        y = np.array(y)
        if X.shape[0] == 0:
            raise ValueError("No training samples generated—data too short")
        self.model.fit(X, y, epochs=10, batch_size=32, verbose=1)
        self.is_trained = True
        self.last_data = scaled_data[-self.window:]
        logging.info(f"LSTM model trained for {self.timeframe} timeframe")

    def predict(self, current_price, volume, sentiment, door1_range, door1_pattern):
        if not self.is_trained or self.last_data is None:
            raise ValueError("Model must be trained with data before predicting")
        data = np.vstack([self.last_data[:-1], [current_price, volume, sentiment]])
        scaled_data = self.scaler.transform(data)
        X = scaled_data.reshape((1, self.window, 3))
        pred_scaled = self.model.predict(X, verbose=0)
        pred_price = self.scaler.inverse_transform([[pred_scaled[0][0], 0, 0]])[0][0]
        low, high = door1_range
        # Narrow the range: ±$200 around predicted price, within Door I bounds
        narrow_low = max(low, pred_price - 200)
        narrow_high = min(high, pred_price + 200)
        return narrow_low, narrow_high