from fastapi import FastAPI, HTTPException
import requests
from cachetools import TTLCache, cached
import sqlite3
from datetime import datetime
import time
import os

app = FastAPI()

# Initialize an in-memory cache with a TTL (Time To Live)
cache = TTLCache(maxsize=100, ttl=3600)

# OpenWeatherMap API details
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"

# Database connection
def get_db_connection():
    conn = sqlite3.connect('weather.db')
    conn.row_factory = sqlite3.Row
    return conn

# Initialize the database
def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS weather (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     city TEXT,
                     date TEXT,
                     min_temp REAL,
                     max_temp REAL,
                     avg_temp REAL,
                     humidity INTEGER)''')
    conn.commit()
    conn.close()

init_db()

# Helper function to calculate average temperature
def calculate_average_temp(min_temp, max_temp):
    return (min_temp + max_temp) / 2

# Fetch weather data from OpenWeatherMap
def fetch_weather_data(city:str, date:datetime):
    date_unix = time.mktime(date.timetuple())
    params = {
        'q': city,
        'dt':date_unix,
        'appid': OPENWEATHER_API_KEY,
        'units': 'metric'
    }
    response = requests.get(BASE_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        min_temp = data['main']['temp_min']
        max_temp = data['main']['temp_max']
        avg_temp = calculate_average_temp(min_temp, max_temp)
        humidity = data['main']['humidity']
        return {
            'min_temp': min_temp,
            'max_temp': max_temp,
            'avg_temp': avg_temp,
            'humidity': humidity,
        }
    else:
        raise HTTPException(status_code=404, detail="City not found")


# Cache the weather data to SQLite to avoid duplicate API calls
def cache_weather_data_in_db(city:str, date:datetime, weather_data:dict):
    conn = get_db_connection()
    try:
        conn.execute('''INSERT OR IGNORE INTO weather (city, date, min_temp, max_temp, avg_temp, humidity)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                     (city, date, weather_data['min_temp'], weather_data['max_temp'],
                      weather_data['avg_temp'], weather_data['humidity']))
        conn.commit()
    finally:
        conn.close()

# Retrieve weather data from the SQLite database
def get_weather_data_from_db(city:str, date:str):
    conn = get_db_connection()
    weather_data = conn.execute('SELECT * FROM weather WHERE city = ? AND date = ?',
                                (city, date)).fetchone()
    conn.close()
    return weather_data

# Cache the weather data
@cached(cache)
def get_cached_weather_data(city, date):
    """
    City: str
    Date: Format (YYYY-MM-DD)
    """
    date_datetime = datetime.strptime(date, "%Y-%m-%d")
    weather_data = get_weather_data_from_db(city, date_datetime)
    if weather_data:
        return dict(weather_data)
    else:
        weather_data = fetch_weather_data(city, date_datetime)
        cache_weather_data_in_db(city, date_datetime, weather_data)
        return weather_data
    

# GET endpoint to retrieve weather data
@app.get("/weather/{city}/{date}")
async def get_weather(city: str, date: str):
    weather_data = get_cached_weather_data(city, date)
    return weather_data