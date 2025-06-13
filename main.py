from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import json
import os

app = FastAPI()

# Статические файлы (HTML)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Хранилище данных (в оперативной памяти)
sensor_data = {}

# ==== POST: приём данных с ESP32 ====
@app.post("/api/sensor")
async def receive_sensor_data(request: Request):
    data = await request.json()
    sensor_data.update(data)
    return {"status": "ok", "received": data}

# ==== GET: HTML интерфейс ====
@app.get("/panel", response_class=HTMLResponse)
async def get_panel():
    # Загружаем HTML-шаблон
    file_path = os.path.join("static", "interface_panel.html")
    with open(file_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Обновляем данные (или показываем "–")
    def val(key):
        return sensor_data.get(key, "–")

    html = html.replace("{{temperature}}", str(val("temperature")))
    html = html.replace("{{humidity}}", str(val("humidity")))
    html = html.replace("{{motion}}", "Да" if val("motion") in [1, True, "true", "True"] else "Нет")
    html = html.replace("{{water}}", str(val("water")))
    html = html.replace("{{rssi}}", str(val("rssi")))
    html = html.replace("{{snr}}", str(val("snr")))
    html = html.replace("{{time}}", datetime.now().strftime("%H:%M:%S"))

    return html

# ==== Корневая страница ====
@app.get("/")
async def root():
    return {"message": "ESP32 Garage Sensor API"}
