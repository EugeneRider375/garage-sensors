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

app.mount("/static", StaticFiles(directory="static"), name="static")

# ===== Базовый шаблон записи =====
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

# ===== Данные =====
# «Как раньше» — одно последнее состояние:
last_data = empty_record()

# Новые 4 слота (окна) — на будущее сразу готовы:
SLOTS = {
    "slot1": empty_record(),
    "slot2": empty_record(),
    "slot3": empty_record(),
    "slot4": empty_record(),
}

relay_state = {"state": "off"}

# Утилита: аккуратно обновить слот
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
    Если пришёл deviceId = slot1|slot2|slot3|slot4 — пишем в соответствующий слот.
    Если deviceId нет — пишем в slot1 (и в last_data, как раньше).
    """
    device_id = str(data.get("deviceId") or "").strip().lower()
    slot = device_id if device_id in SLOTS else "slot1"

    # обновим соответствующий слот
    rec = update_slot(slot, data)

    # поведение «как раньше»: одно глобальное значение
    global last_data
    last_data = dict(rec)  # копия, чтобы панель видела тот же формат

    return {"message": "Data received", "slot": slot}

@app.get("/api/data")
async def get_data():
    # Старый эндпоинт — без изменений
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

# НОВОЕ: дополнительная страница с 4 «окнами» (ничего в статике менять не нужно)
@app.get("/panel_multi", response_class=HTMLResponse)
async def panel_multi(request: Request):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/")
    # Простая адаптивная сетка на 4 карточки
    return HTMLResponse("""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Garage Panel – Multi</title>
  <style>
    body{font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial; margin:0; background:#0b0d12; color:#e6eef7;}
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
