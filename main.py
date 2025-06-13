from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()

last_data = {
    "temperature": None,
    "humidity": None,
    "motion": None,
    "water": None,
    "rssi": None,
    "snr": None,
    "time": None
}

class SensorData(BaseModel):
    temperature: float
    humidity: float
    motion: bool
    water: int
    rssi: int
    snr: float

@app.post("/api/sensor")
async def receive_sensor_data(data: SensorData):
    last_data.update({
        "temperature": data.temperature,
        "humidity": data.humidity,
        "motion": data.motion,
        "water": data.water,
        "rssi": data.rssi,
        "snr": data.snr,
        "time": datetime.now().strftime("%H:%M:%S")
    })
    return {"status": "ok"}

@app.get("/", response_class=PlainTextResponse)
async def show_data():
    if last_data["temperature"] is None:
        return "Нет данных"

    m = "Да" if last_data["motion"] else "Нет"
    return (
        f"📡 Данные: "
        f"T={last_data['temperature']}°C "
        f"H={last_data['humidity']}% "
        f"M={m} "
        f"W={last_data['water']} "
        f"RSSI={last_data['rssi']} "
        f"SNR={last_data['snr']} "
        f"🕒 {last_data['time']}"
    )
