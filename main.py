from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

sensor_data = {}

@app.post("/api/sensor")
async def receive_sensor_data(request: Request):
    data = await request.json()
    sensor_data.update(data)
    return {"status": "ok", "received": data}

@app.get("/panel", response_class=HTMLResponse)
async def panel():
    html = f"""
    <html>
    <head><title>Garage Sensors Panel</title></head>
    <body>
        <h1>Данные с датчиков</h1>
        <pre>{sensor_data}</pre>
    </body>
    </html>
    """
    return html
