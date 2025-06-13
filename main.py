from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import datetime

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# Переменная для хранения последних данных
latest_data = {
    "temperature": None,
    "humidity": None,
    "motion": None,
    "water": None,
    "rssi": None,
    "snr": None,
    "time": None,
}

@app.post("/api/sensor")
async def receive_data(request: Request):
    global latest_data
    try:
        data = await request.json()
        data["time"] = datetime.datetime.now().strftime("%H:%M:%S")
        latest_data.update(data)
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

@app.get("/api/data")
async def get_data():
    return latest_data

@app.get("/panel", response_class=HTMLResponse)
async def serve_panel():
    with open("static/interface_panel.html", "r", encoding="utf-8") as f:
        html = f.read()
        return HTMLResponse(content=html)
