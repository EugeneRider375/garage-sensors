from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from starlette.responses import Response
import datetime
import os

# === NEW: для раздельного хранения по устройствам ===
from typing import Dict, Any
from collections import deque
LATEST_BY_DEVICE: Dict[str, Dict[str, Any]] = {}
HISTORY = deque(maxlen=1000)  # опционально; можно удалить, если история не нужна
# === /NEW ===

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")

# Данные (глобальное «последнее вообще» — как было)
last_data = {
    "temperature": None,
    "humidity": None,
    "motion": None,
    "water": None,
    "rssi": None,
    "snr": None,
    "time": None,
}
relay_state = {"state": "off"}

# ===== API =====

@app.post("/api/sensor")
async def receive_sensor_data(data: dict):
    """
    Принимаем произвольный JSON от устройств.
    Сохраняем:
      1) last_data — «последнее вообще» (как раньше)
      2) LATEST_BY_DEVICE[deviceId] — «последнее по устройству»
    """
    # серверсайд-время (строка для панели)
    data["time"] = datetime.datetime.now().strftime("%H:%M:%S")

    # слегка нормализуем числа (не обязательно, но удобно)
    if "temperature" in data and isinstance(data["temperature"], (int, float)):
        data["temperature"] = round(float(data["temperature"]), 1)
    if "humidity" in data and isinstance(data["humidity"], (int, float)):
        data["humidity"] = round(float(data["humidity"]), 1)

    # 1) как раньше — перезатираем глобальное «последнее»
    global last_data
    last_data = data

    # 2) NEW — сохраняем «последнее по устройству»
    device_id = str(data.get("deviceId") or "default")
    # кладём копию, чтобы внешний код не мутировал наш словарь
    LATEST_BY_DEVICE[device_id] = dict(data)
    HISTORY.append({**data, "deviceId": device_id})

    return {"message": "Data received"}

@app.get("/api/data")
async def get_data():
    """Старый формат — последнее «вообще» (для текущей панели)."""
    return last_data

# === NEW: раздельные данные по устройствам ===
@app.get("/api/devices")
async def get_devices():
    """
    Возвращает последнее состояние по каждому deviceId.
    {
      "devices": ["garage-1", "garage-2", "esp32-local"],
      "data": { "garage-1": {...}, "garage-2": {...}, "esp32-local": {...} }
    }
    """
    return {
        "devices": list(LATEST_BY_DEVICE.keys()),
        "data": LATEST_BY_DEVICE
    }
# === /NEW ===

@app.get("/api/relay")
async def get_relay_state():
    return JSONResponse(content=relay_state)

@app.post("/api/relay")
async def set_relay_state(request: Request):
    data = await request.json()
    state = data.get("state")
    if state in ["on", "off"]:
        relay_state["state"] = state
        return JSONResponse(content={"status": "success", "new_state": state})
    else:
        return JSONResponse(content={"status": "error", "message": "Invalid state"}, status_code=400)

# ===== Аутентификация / Страницы =====

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    if request.cookies.get("auth") == "true":
        return RedirectResponse(url="/panel")
    return FileResponse("static/login.html")

@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "1234":
        response = RedirectResponse(url="/panel", status_code=302)
        response.set_cookie(key="auth", value="true", httponly=True)
        return response
    return HTMLResponse("<h3>Неверный логин или пароль</h3><a href='/'>Назад</a>")

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("auth")
    return response

@app.get("/panel", response_class=HTMLResponse)
async def get_panel(request: Request):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/")
    return FileResponse(os.path.join("static", "interface_panel.html"))
