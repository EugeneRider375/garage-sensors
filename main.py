from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime
import os

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")

# Хранилище последнего состояния
latest_data = {
    "temperature": None,
    "humidity": None,
    "motion": "Нет",
    "water": None,
    "rssi": None,
    "snr": None,
    "time": "-"
}

@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse("<h1>Garage Sensor Server</h1><p>Use <a href='/panel'>/panel</a> to view data.</p>")

@app.get("/panel", response_class=HTMLResponse)
async def get_panel(request: Request):
    return templates.TemplateResponse("interface_panel.html", {
        "request": request,
        **latest_data,
        "time": datetime.now().strftime("%H:%M:%S")
    })

@app.post("/api/sensor")
async def receive_sensor_data(data: dict):
    try:
        latest_data.update({
            "temperature": data.get("temperature"),
            "humidity": data.get("humidity"),
            "motion": "Да" if data.get("motion") else "Нет",
            "water": data.get("water"),
            "rssi": data.get("rssi"),
            "snr": data.get("snr"),
        })
        return {"status": "ok", "received": latest_data}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

@app.get("/api/data")
async def get_latest_data():
    return latest_data
