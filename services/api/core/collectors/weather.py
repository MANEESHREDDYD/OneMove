from typing import Optional

import httpx
from pydantic import BaseModel


class WeatherData(BaseModel):
    temperature_2m: float
    precipitation: float
    wind_speed_10m: float
    weather_code: int


class OpenMeteoCollector:
    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self.client = client or httpx.AsyncClient()

    async def fetch_current_weather(self, lat: float, lon: float) -> WeatherData:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,precipitation,weather_code,wind_speed_10m",
            "timezone": "auto",
        }

        response = await self.client.get(self.BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        current = data.get("current", {})

        return WeatherData(
            temperature_2m=current.get("temperature_2m", 0.0),
            precipitation=current.get("precipitation", 0.0),
            wind_speed_10m=current.get("wind_speed_10m", 0.0),
            weather_code=current.get("weather_code", 0),
        )
