
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

latest_data = {
    "temperature": None,
    "humidity": None,
    "motion": None,
    "water": None,
    "rssi": None,
    "snr": None,
    "time": None
}

class SensorData(BaseModel):
    temperature: float | None = None
    humidity: float | None = None
    motion: bool | None = None
    water: int | None = None
    rssi: int | None = None
    snr: float | None = None

@app.post("/api/sensor")
async def receive_sensor_data(data: SensorData):
    latest_data.update(data.dict())
    latest_data["time"] = datetime.now().strftime("%H:%M:%S")
    return {"message": "Data received"}

@app.get("/", response_class=HTMLResponse)
async def get_data():
    return f'''
        <html><body>
        <h2>Garage Sensor Data</h2>
        <p><b>🌡️ Temp:</b> {latest_data["temperature"]} °C</p>
        <p><b>💧 Hum:</b> {latest_data["humidity"]} %</p>
        <p><b>🚪 Motion:</b> {"Да" if latest_data["motion"] else "Нет"}</p>
        <p><b>🌊 Water:</b> {latest_data["water"]}</p>
        <p><b>📶 RSSI:</b> {latest_data["rssi"]}</p>
        <p><b>SNR:</b> {latest_data["snr"]}</p>
        <p><b>⏱ Время:</b> {latest_data["time"]}</p>
        </body></html>
    '''
