from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Получение данных с датчиков
@app.post("/api/sensor")
async def receive_sensor_data(data: dict):
    global last_data
    data["time"] = datetime.datetime.now().strftime("%H:%M:%S")
    last_data = data
    return {"message": "Data received"}

# Получение текущих данных
@app.get("/api/data")
async def get_data():
    return last_data

# Получение состояния реле
@app.get("/api/relay")
async def get_relay_state():
    return JSONResponse(content=relay_state)

# Изменение состояния реле
@app.post("/api/relay")
async def set_relay_state(request: Request):
    data = await request.json()
    state = data.get("state")
    if state in ["on", "off"]:
        relay_state["state"] = state
        return JSONResponse(content={"status": "success", "new_state": state})
    else:
        return JSONResponse(content={"status": "error", "message": "Invalid state"}, status_code=400)

# HTML-страница мониторинга + управление реле
@app.get("/panel", response_class=HTMLResponse)
async def get_panel():
    html = f"""
    <html>
        <head>
            <meta charset="UTF-8">
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
                button {{
                    margin-right: 10px;
                    padding: 10px 20px;
                    font-size: 14px;
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
                <!-- Закомментированные LoRa параметры -->
                <!-- <div class="item">📶 RSSI: {last_data["rssi"]}</div> -->
                <!-- <div class="item">📡 SNR: {last_data["snr"]}</div> -->
                <div class="item">⏰ Время: {last_data["time"]}</div>

                <hr>

                <h3>🖲️ Управление реле</h3>
                <div class="item">Текущее состояние: {relay_state["state"]}</div>
                <button onclick="setRelay('on')">Включить реле</button>
                <button onclick="setRelay('off')">Выключить реле</button>
                <p id="relayStatus"></p>
            </div>

            <script>
                async function setRelay(state) {{
                    try {{
                        const response = await fetch('/api/relay', {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json'
                            }},
                            body: JSON.stringify({{state}})
                        }});
                        const result = await response.json();
                        document.getElementById('relayStatus').innerText = 'Ответ: ' + JSON.stringify(result);
                    }} catch (error) {{
                        console.error('Ошибка:', error);
                    }}
                }}
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html)
