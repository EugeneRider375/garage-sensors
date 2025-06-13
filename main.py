from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import time

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

sensor_data = {}

class SensorPayload(BaseModel):
    temperature: float
    humidity: float
    motion: bool
    water: int = 0
    rssi: int = 0
    snr: float = 0.0

@app.post("/api/sensor")
async def receive_sensor_data(payload: SensorPayload):
    global sensor_data
    sensor_data = payload.dict()
    return {"status": "ok", "received": sensor_data}

@app.get("/panel", response_class=HTMLResponse)
async def panel():
    return f"""
    <html>
        <head><title>Данные с датчиков</title></head>
        <body>
            <h1>Данные с датчиков</h1>
            <pre>{sensor_data}</pre>
        </body>
    </html>
    """