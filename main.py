
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

last_data = {
    "temperature": None,
    "humidity": None,
    "motion": None,
    "water": None,
    "rssi": None,
    "snr": None,
    "time": None,
}

@app.post("/api/sensor")
async def receive_sensor_data(data: dict):
    global last_data
    data["time"] = datetime.datetime.now().strftime("%H:%M:%S")
    last_data = data
    return {"message": "Data received"}

@app.get("/api/data")
async def get_data():
    return last_data

@app.get("/panel", response_class=HTMLResponse)
async def get_panel():
    html = f"""
    <html>
        <head>
            <meta charset="UTF-8">
            <meta http-equiv="refresh" content="3">
            <style>
                body {{
                    font-family: sans-serif;
                    padding: 20px;
                    background: #f9f9f9;
                }}
                .card {{
                    background: white;
                    border-radius: 10px;
                    padding: 20px;
                    max-width: 400px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }}
                .item {{
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            <div class="card">
                <h2>📡 Мониторинг</h2>
                <div class="item">🌡️ Температура: {last_data["temperature"]} °C</div>
                <div class="item">💧 Влажность: {last_data["humidity"]} %</div>
                <div class="item">🚶 Движение: {"Да" if last_data["motion"] else "Нет"}</div>
                <div class="item">🌊 Вода: {last_data["water"]}</div>
                <div class="item">📶 RSSI: {last_data["rssi"]}</div>
                <div class="item">📡 SNR: {last_data["snr"]}</div>
                <div class="item">⏰ Время: {last_data["time"]}</div>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=html)
