import pytest
import json
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_init_endpoint(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b"IRIS Crypto Trading API" in response.data

def test_api_status_endpoint(client):
    response = client.get('/api/status')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['api_name'] == "IRIS Crypto Trading API"
    assert "price_prediction" in data['features']

def test_health_check_endpoint(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == "healthy"
    assert data['service'] == "IRIS Crypto Trading API"

def test_predict_endpoint_all_symbols(client):
    response = client.post('/api/predict', json={'symbol': 'ALL'})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'predictions' in data
    assert isinstance(data['predictions'], list)

def test_predict_endpoint_specific_symbol(client):
    response = client.post('/api/predict', json={'symbol': 'BTC'})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'symbol' in data
    assert data['symbol'] == 'BTC'

def test_predict_endpoint_invalid_symbol(client):
    response = client.post('/api/predict', json={'symbol': 'INVALID'})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data
    assert 'Unsupported symbol' in data['error']

# def test_get_predictions_endpoint(client): # Requires a database connection
#     response = client.get('/api/predictions')
#     assert response.status_code == 200
#     data = json.loads(response.data)
#     assert 'predictions' in data
#     assert isinstance(data['predictions'], list)

# def test_trade_endpoint(client): # Requires Binance API keys
#     response = client.post('/api/trade', json={
#         'symbol': 'BTCUSDT',
#         'quantity': 0.01,
#         'side': 'BUY',
#         'api_key': 'YOUR_BINANCE_API_KEY',
#         'secret_key': 'YOUR_BINANCE_SECRET_KEY'
#     })
#     assert response.status_code == 400 # Expecting error due to missing API keys or invalid symbol

def test_chat_endpoint(client):
    response = client.post('/api/chat', json={'message': 'Hello'})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'reply' in data

def test_chat_endpoint_empty_message(client):
    response = client.post('/api/chat', json={'message': ''})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'reply' in data
