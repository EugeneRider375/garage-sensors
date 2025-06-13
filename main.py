from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import datetime

app = FastAPI()

# Хранилище данных
latest_data = {
    "temperature": None,
    "humidity": None,
    "motion": None,
    "water": None,
    "rssi": None,
    "snr": None,
    "time": None,
}

# Разрешим CORS для любого источника (если потребуется)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/sensor")
async def receive_sensor_data(request: Request):
    data = await request.json()
    latest_data.update(data)
    latest_data["time"] = datetime.datetime.now().strftime("%H:%M:%S")
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def show_data():
    return f"""<html><body>
    <h2>📡 Мониторинг</h2>
    <p>🌡 Температура: {latest_data['temperature']} °C</p>
    <p>💧 Влажность: {latest_data['humidity']} %</p>
    <p>🚪 Движение: {'Да' if latest_data['motion'] else 'Нет'}</p>
    <p>🌊 Вода: {latest_data['water']}</p>
    <p>📶 RSSI: {latest_data['rssi']}</p>
    <p>SNR: {latest_data['snr']}</p>
    <p>⏱ Время: {latest_data['time']}</p>
    </body></html>"""
