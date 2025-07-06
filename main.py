from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import datetime
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Хранение последних данных с датчиков
last_data = {
    "temperature": None,
    "humidity": None,
    "motion": None,
    "water": None,
    "rssi": None,
    "snr": None,
    "time": None,
}

# Состояние реле
relay_state = {"state": "off"}

@app.post("/api/sensor")
async def receive_sensor_data(data: dict):
    global last_data
    data["time"] = datetime.datetime.now().strftime("%H:%M:%S")
    last_data = data
    return {"message": "Data received"}

@app.get("/api/data")
async def get_data():
    return last_data

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

@app.get("/panel", response_class=HTMLResponse)
async def get_panel_file():
    return FileResponse(os.path.join("static", "interface_panel.html"))
