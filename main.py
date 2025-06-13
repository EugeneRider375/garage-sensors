from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
import os

app = FastAPI()

# === ПАПКА STATIC ===
app.mount("/static", StaticFiles(directory="static"), name="static")

# === ГЛОБАЛЬНОЕ ХРАНИЛИЩЕ ДАННЫХ ===
sensor_data = {
    "temperature": None,
    "humidity": None,
    "motion": False,
    "water": None,
    "rssi": None,
    "snr": None,
    "time": "--:--:--"
}

# === ОБРАБОТЧИК ГЛАВНОЙ СТРАНИЦЫ ===
@app.get("/panel", response_class=HTMLResponse)
async def get_panel():
    file_path = os.path.join("static", "interface_panel.html")
    with open(file_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content, status_code=200)

# === ЭНДПОИНТ ДЛЯ ПОЛУЧЕНИЯ АКТУАЛЬНЫХ ДАННЫХ ===
@app.get("/api/data")
async def get_data():
    return JSONResponse(content=sensor_data)

# === ЭНДПОИНТ ДЛЯ ПОЛУЧЕНИЯ ДАННЫХ ОТ ESP32 ===
@app.post("/api/sensor")
async def post_sensor_data(request: Request):
    try:
        payload = await request.json()

        # Обновляем глобальные данные
        sensor_data["temperature"] = payload.get("temperature")
        sensor_data["humidity"] = payload.get("humidity")
        sensor_data["motion"] = payload.get("motion")
        sensor_data["water"] = payload.get("water")
        sensor_data["rssi"] = payload.get("rssi")
        sensor_data["snr"] = payload.get("snr")
        sensor_data["time"] = datetime.now().strftime("%H:%M:%S")

        return {"status": "ok", "received": sensor_data}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
