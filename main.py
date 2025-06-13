
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json
from datetime import datetime

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# Хранилище последних данных
latest_data = {}

class SensorData(BaseModel):
    temperature: float
    humidity: float
    motion: bool
    water: int = 0
    rssi: int = 0
    snr: float = 0.0

@app.post("/api/sensor")
async def receive_sensor_data(data: SensorData):
    global latest_data
    latest_data = data.dict()
    return {"status": "ok", "received": latest_data}

@app.get("/api/data")
async def get_data():
    return latest_data

@app.get("/panel", response_class=HTMLResponse)
async def panel(request: Request):
    now = datetime.now().strftime("%H:%M:%S")
    data = {
        "temperature": latest_data.get("temperature", "–"),
        "humidity": latest_data.get("humidity", "–"),
        "motion": "Да" if latest_data.get("motion") else "Нет",
        "water": latest_data.get("water", "–"),
        "rssi": latest_data.get("rssi", "–"),
        "snr": latest_data.get("snr", "–"),
        "time": now
    }
    with open("static/interface_panel.html", "r") as f:
        html = f.read()
        for key, value in data.items():
            html = html.replace(f"{{{{ {key} }}}}", str(value))
    return HTMLResponse(content=html)
