from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import datetime
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# статика и старая панель остаются как были
app.mount("/static", StaticFiles(directory="static"), name="static")

# ===== базовый шаблон записи =====
def empty_record():
    return {
        "temperature": None,
        "humidity": None,
        "motion": None,
        "water": None,
        "rssi": None,
        "snr": None,
        "time": None,
        "deviceId": None,
    }

# ===== данные =====
# одно «последнее вообще» — для /api/data и /panel (как раньше)
last_data = empty_record()

# 4 слота (окна) для параллельных источников
SLOTS = {
    "slot1": empty_record(),
    "slot2": empty_record(),
    "slot3": empty_record(),
    "slot4": empty_record(),
}

# алиасы: твои текущие deviceId -> нужный слот (чтобы прошивки не трогать)
DEVICE_SLOT_MAP = {
    "garage-1": "slot1",
    "garage-2": "slot2",
    "esp32-local": "slot3",   # можно задать в прошивке ESP32 позже
    # добавляй при необходимости
}

relay_state = {"state": "off"}

# утилита: аккуратно обновить слот
def update_slot(slot_name: str, data: dict):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    rec = {
        "temperature": data.get("temperature"),
        "humidity": data.get("humidity"),
        "motion": data.get("motion"),
        "water": data.get("water"),
        "rssi": data.get("rssi"),
        "snr": data.get("snr"),
        "time": now,
        "deviceId": data.get("deviceId") or slot_name,
    }
    SLOTS[slot_name] = rec
    return rec

# ===== API =====

@app.post("/api/sensor")
async def receive_sensor_data(data: dict):
    """
    Совместимо со старым форматом.
    Если deviceId = 'garage-1'/'garage-2'/... — используем алиас в нужный слот.
    Если deviceId = 'slot1'..'slot4' — пишем прямо в этот слот.
    Если deviceId нет — используем slot1.
    """
    device_raw = data.get("deviceId")
    device_id = str(device_raw).strip().lower() if device_raw is not None else ""

    # алиас → слот
    slot = DEVICE_SLOT_MAP.get(device_id)
    if not slot:
        # если уже приходит slot1..slot4 — используем как есть
        slot = device_id if device_id in SLOTS else "slot1"

    # обновляем слот
    rec = update_slot(slot, data)

    # поведение «как раньше»: одно глобальное значение
    global last_data
    last_data = dict(rec)

    return {"message": "Data received", "slot": slot}

@app.get("/api/data")
async def get_data():
    # старый эндпоинт — без изменений
    return last_data

# НОВОЕ: все 4 слота разом
@app.get("/api/data_multi")
async def get_data_multi():
    return SLOTS

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

# ===== аутентификация / страницы =====

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

# НОВОЕ: простая страница с 4 карточками (не правим твою статику)
@app.get("/panel_multi", response_class=HTMLResponse)
async def panel_multi(request: Request):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/")
    return HTMLResponse("""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Garage Panel – Multi</title>
  <style>
    body{font-family: system-ui,-apple-system,Segoe UI,Roboto,Arial; margin:0; background:#0b0d12; color:#e6eef7;}
    header{padding:12px 16px; background:#0f131a; border-bottom:1px solid #1b2330;}
    h1{margin:0; font-size:18px;}
    .grid{display:grid; gap:16px; padding:16px; grid-template-columns: repeat(auto-fit, minmax(260px,1fr));}
    .card{background:#101620; border:1px solid #1c2533; border-radius:14px; padding:14px;}
    .row{display:flex; justify-content:space-between; margin:6px 0;}
    .muted{opacity:.7; font-size:12px;}
    .id{font-weight:600;}
    small{opacity:.8;}
  </style>
</head>
<body>
  <header>
    <h1>Garage Panel — Multi <small class="muted">/api/data_multi</small></h1>
  </header>
  <div class="grid" id="grid"></div>

<script>
const slotsOrder = ["slot1","slot2","slot3","slot4"];
function render(data){
  const grid = document.getElementById('grid');
  grid.innerHTML = '';
  slotsOrder.forEach(k=>{
    const d = data[k] || {};
    const el = document.createElement('div');
    el.className = 'card';
    el.innerHTML = `
      <div class="row"><span class="id">${d.deviceId || k}</span><span class="muted">${d.time || ''}</span></div>
      <div class="row"><span>Темп.</span><span>${fmt(d.temperature)} °C</span></div>
      <div class="row"><span>Влажн.</span><span>${fmt(d.humidity)} %</span></div>
      <div class="row"><span>Движение</span><span>${fmtBool(d.motion)}</span></div>
      <div class="row"><span>Вода</span><span>${fmt(d.water)}</span></div>
      ${d.rssi !== undefined ? `<div class="row"><span>RSSI</span><span>${fmt(d.rssi)}</span></div>` : ''}
      ${d.snr  !== undefined ? `<div class="row"><span>SNR</span><span>${fmt(d.snr)}</span></div>` : ''}
    `;
    grid.appendChild(el);
  });
}
function fmt(v){ return (v===null || v===undefined) ? '—' : v; }
function fmtBool(b){ return (b===null || b===undefined) ? '—' : (b ? 'Да' : 'Нет'); }

async function tick(){
  try{
    const r = await fetch('/api/data_multi', {cache:'no-store'});
    const j = await r.json();
    render(j);
  }catch(e){
    console.error(e);
  }
}
tick(); setInterval(tick, 3000);
</script>
</body>
</html>
    """)
