
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import json

app = FastAPI()

# Подключение папки static
app.mount("/static", StaticFiles(directory="static"), name="static")

# Глобальное хранилище последних данных
latest_data = {}

@app.post("/api/sensor")
async def receive_sensor_data(request: Request):
    global latest_data
    latest_data = await request.json()
    return {"status": "ok", "received": latest_data}

@app.get("/panel", response_class=HTMLResponse)
async def panel():
    global latest_data
    html_path = "static/interface_panel.html"
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            template = f.read()
        # Подготовка значений
        data = {
            "temperature": latest_data.get("temperature", "–"),
            "humidity": latest_data.get("humidity", "–"),
            "motion": "Да" if latest_data.get("motion") else "Нет",
            "water": latest_data.get("water", "–"),
            "rssi": latest_data.get("rssi", "–"),
            "snr": latest_data.get("snr", "–"),
            "time": datetime.now().strftime("%H:%M:%S")
        }
        # Замена плейсхолдеров в шаблоне
        for key, value in data.items():
            template = template.replace(f"{{{{ {key} }}}}", str(value))
        return HTMLResponse(content=template)
    except Exception as e:
        return HTMLResponse(content=f"<h2>Ошибка: {e}</h2>")
