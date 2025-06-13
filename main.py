from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import datetime

app = FastAPI()

# Глобальное хранилище последних данных
latest_data = {
    "temperature": None,
    "humidity": None,
    "motion": None,
    "water": None,
    "rssi": None,
    "snr": None,
    "time": None
}

# Подключаем папку static
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    return "<h1>Garage Sensor Project</h1>"

@app.post("/api/sensor")
async def receive_data(data: dict):
    data["time"] = datetime.datetime.now().strftime("%H:%M:%S")
    latest_data.update(data)
    return {"status": "ok", "received": data}

@app.get("/api/data")
async def get_data():
    return latest_data

@app.get("/panel", response_class=HTMLResponse)
async def show_panel(request: Request):
    return templates.TemplateResponse("interface_panel.html", {"request": request, **latest_data})
