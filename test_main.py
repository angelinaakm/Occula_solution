
import pytest
import requests
from unittest.mock import patch
from datetime import datetime
from main import fetch_weather_data, calculate_average_temp, get_cached_weather_data, app


# Example for patching the fetch_weather_data to avoid actual API calls
@patch('main.requests.get')
def test_fetch_weather_data(mock_get):
    # Mock the JSON response from OpenWeatherMap API
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = {
        'main': {
            'temp_min': 10.0,
            'temp_max': 20.0,
            'humidity': 60
        }
    }
    
    city = "London"
    date = "2024-08-14"
    date = datetime.strptime(date, "%Y-%m-%d")
    
    # Call the function
    result = fetch_weather_data(city, date)
    
    # Assert the expected values
    assert result['min_temp'] == 10.0
    assert result['max_temp'] == 20.0
    assert result['avg_temp'] == calculate_average_temp(10.0, 20.0)
    assert result['humidity'] == 60

def test_calculate_average_temp():
    min_temp = 10.0
    max_temp = 20.0
    avg_temp = calculate_average_temp(min_temp, max_temp)
    assert avg_temp == 15.0

@patch('main.get_weather_data_from_db')
@patch('main.fetch_weather_data')
def test_get_cached_weather_data(mock_fetch, mock_db):
    # Mock fetch_weather_data and get_weather_data_from_db
    mock_fetch.return_value = {
        'min_temp': 10.0,
        'max_temp': 20.0,
        'avg_temp': 15.0,
        'humidity': 60
    }
    
    mock_db.return_value = None  # Simulate cache miss

    city = "London"
    date = "2024-08-14"
    
    # Call the function
    result = get_cached_weather_data(city, date)
    
    # Assert the expected values
    assert result['min_temp'] == 10.0
    assert result['max_temp'] == 20.0
    assert result['avg_temp'] == 15.0
    assert result['humidity'] == 60

@patch('main.get_cached_weather_data')
def test_get_weather_endpoint(mock_get_cached):
    # Mock the cached data
    mock_get_cached.return_value = {
        'min_temp': 10.0,
        'max_temp': 20.0,
        'avg_temp': 15.0,
        'humidity': 60
    }
    
    # Create a test client
    from fastapi.testclient import TestClient
    client = TestClient(app)
    
    # Make a request to the API endpoint
    response = client.get("/weather/London/2024-08-14")
    
    # Assert the response
    assert response.status_code == 200
    assert response.json() == {
        'min_temp': 10.0,
        'max_temp': 20.0,
        'avg_temp': 15.0,
        'humidity': 60
    }