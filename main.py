from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import datetime
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SessionMiddleware, secret_key="verysecretkey")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Данные с датчиков
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

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    if request.session.get("user") == "admin":
        return RedirectResponse(url="/panel")
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
async def login_form():
    return FileResponse("static/login.html")

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == "admin" and password == "1234":
        request.session["user"] = username
        return RedirectResponse(url="/panel", status_code=302)
    return HTMLResponse("<h3>Неверный логин или пароль</h3><a href='/login'>Попробовать снова</a>", status_code=401)

@app.get("/panel", response_class=HTMLResponse)
async def get_panel_file(request: Request):
    if request.session.get("user") != "admin":
        return RedirectResponse(url="/login")
    return FileResponse(os.path.join("static", "interface_panel.html"))

@app.post("/api/sensor")
async def receive_sensor_data(data: dict):
    data["time"] = datetime.datetime.now().strftime("%H:%M:%S")
    global last_data
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
    return JSONResponse(content={"status": "error", "message": "Invalid state"}, status_code=400)
