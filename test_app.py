import pytest
import json
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_predict_all(client):
    response = client.post('/api/predict', json={'symbol': 'ALL'})
    assert response.status_code == 200
    data = json.loads(response.data.decode('utf-8'))
    assert 'predictions' in data
    assert isinstance(data['predictions'], list)

def test_predict_single(client):
    response = client.post('/api/predict', json={'symbol': 'BTC'})
    assert response.status_code == 200
    data = json.loads(response.data.decode('utf-8'))
    assert 'coin' in data

def test_predict_invalid_symbol(client):
    response = client.post('/api/predict', json={'symbol': 'INVALID'})
    assert response.status_code == 400
    data = json.loads(response.data.decode('utf-8'))
    assert 'error' in data

def test_get_predictions(client):
    response = client.get('/api/predictions')
    assert response.status_code == 200
    data = json.loads(response.data.decode('utf-8'))
    assert 'predictions' in data
    assert isinstance(data['predictions'], list)

def test_trade_valid(client):
    # Replace with your actual API key and secret key for testing
    api_key = "test_api_key"
    secret_key = "test_secret_key"
    response = client.post('/api/trade', json={
        'symbol': 'BTCUSDT',
        'quantity': 0.01,
        'side': 'BUY',
        'api_key': api_key,
        'secret_key': secret_key
    })
    assert response.status_code == 500 # Expecting 500 since test keys will not work
    data = json.loads(response.data.decode('utf-8'))
    assert 'error' in data

def test_trade_invalid_side(client):
    response = client.post('/api/trade', json={
        'symbol': 'BTCUSDT',
        'quantity': 0.01,
        'side': 'INVALID',
        'api_key': 'test_api_key',
        'secret_key': 'test_secret_key'
    })
    assert response.status_code == 400
    data = json.loads(response.data.decode('utf-8'))
    assert 'error' in data

def test_chat_valid(client):
    response = client.post('/api/chat', json={'message': 'Hello'})
    if response.status_code == 200:
        data = json.loads(response.data.decode('utf-8'))
        assert 'reply' in data
    else:
        assert response.status_code == 500
        data = json.loads(response.data.decode('utf-8'))
        assert 'reply' in data

def test_chat_news(client):
    response = client.post('/api/chat', json={'message': 'Give me the latest news'})
    if response.status_code == 200:
        data = json.loads(response.data.decode('utf-8'))
        assert 'reply' in data
    else:
        assert response.status_code == 500
        data = json.loads(response.data.decode('utf-8'))
        assert 'reply' in data
