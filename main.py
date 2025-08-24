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

# Статика и старая панель остаются как были
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
# Одно «последнее вообще» — для /api/data и /panel (как раньше)
last_data = empty_record()

# 4 слота (окна) для параллельных источников
SLOTS = {
    "slot1": empty_record(),
    "slot2": empty_record(),
    "slot3": empty_record(),
    "slot4": empty_record(),
}

# Алиасы: твои deviceId -> нужный слот (чтобы прошивки не трогать)
DEVICE_SLOT_MAP = {
    "garage-1": "slot1",
    "garage-2": "slot2",
    "old-garage": "slot3",   # самый первый источник без deviceId (ESP32 HTTPClient)
    "esp32-local": "slot3",  # можно задать в прошивке ESP32 позже
    # добавляй при необходимости
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
async def receive_sensor_data(request: Request, data: dict):
    """
    Совместимо со старым форматом.
    Логика выбора слота:
      1) Если data.deviceId в алиасах -> соответствующий слот.
      2) Если data.deviceId = slot1..slot4 -> прямой слот.
      3) Если deviceId нет:
         - если User-Agent содержит 'esp32httpclient' -> считаем 'old-garage' -> slot3
         - иначе по умолчанию slot1.
    """
    # 1) нормализуем deviceId из тела
    device_raw = data.get("deviceId")
    device_id = str(device_raw).strip().lower() if device_raw is not None else ""

    # 2) если deviceId не передан — попробуем узнать по User-Agent
    if not device_id:
        ua = (request.headers.get("user-agent") or "").lower()
        if "esp32httpclient" in ua:
            device_id = "old-garage"  # старый ESP32 с HTTPClient

    # 3) алиас -> слот
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
    # Старый эндпоинт — без изменений
    return last_data

# Новое: все 4 слота разом
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

# ===== Аутентификация / страницы =====

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

# Новое: светлая французская панель 2×2 (адаптивная) — /panel_multi
@app.get("/panel_multi", response_class=HTMLResponse)
async def panel_multi(request: Request):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/")
    return HTMLResponse('''<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Panneau Multi</title>
  <style>
    :root{
      --bg:#ffffff; --fg:#111111; --muted:#6b7280;
      --card:#ffffff; --border:#e5e7eb; --shadow:0 10px 24px rgba(0,0,0,.06);
      --ok:#16a34a; --warn:#f59e0b; --bad:#ef4444; --accent:#2563eb;
      --chip-bg:#f8fafc;
    }
    *{box-sizing:border-box} html,body{height:100%}
    body{margin:0; background:var(--bg); color:var(--fg); font:14px/1.5 system-ui,-apple-system,Segoe UI,Roboto,Arial}
    header{
      position:sticky; top:0; z-index:10;
      background:linear-gradient(#fff,rgba(255,255,255,.92));
      border-bottom:1px solid var(--border);
      padding:14px 18px; display:flex; align-items:center; justify-content:space-between
    }
    h1{margin:0; font-size:18px; font-weight:650}
    .muted{color:var(--muted)}
    .wrap{max-width:1100px; margin:0 auto; padding:18px}

    /* 2×2 desktop, 1×N mobile */
    .grid{display:grid; gap:16px; grid-template-columns: repeat(2, minmax(280px, 1fr))}
    @media (max-width: 840px){ .grid{grid-template-columns: 1fr} }

    .card{
      background:var(--card); border:1px solid var(--border); border-radius:16px;
      box-shadow:var(--shadow); overflow:hidden;
      transition:transform .15s ease, box-shadow .15s ease;
    }
    .card:hover{ transform:translateY(-2px); box-shadow:0 16px 32px rgba(0,0,0,.08) }

    .card-head{
      display:flex; justify-content:space-between; align-items:center;
      padding:12px 16px; background:linear-gradient(180deg,#f8fafc,#ffffff);
      border-bottom:1px solid var(--border);
    }
    .id{font-weight:700; font-size:16px; display:flex; align-items:center; gap:8px}
    .time{opacity:.7}
    .chip{
      display:inline-flex; align-items:center; gap:6px;
      padding:2px 8px; border-radius:999px; border:1px solid var(--border);
      font-size:12px; color:var(--muted); background:var(--chip-bg)
    }
    .dot{width:8px; height:8px; border-radius:50%}
    .ok  .dot{background:var(--ok)}
    .warn .dot{background:var(--warn)}
    .bad .dot{background:var(--bad)}

    .card-body{ padding:12px 16px 14px }
    .row{display:flex; justify-content:space-between; padding:8px 0; border-top:1px dashed var(--border)}
    .row:first-of-type{border-top:none}
    .label{opacity:.85; display:flex; align-items:center; gap:8px}
    .value{font-weight:600}

    .pill{display:inline-block; padding:0 8px; border-radius:999px; border:1px solid var(--border);
      margin-left:8px; font-size:12px; color:var(--muted); background:#f8fafc}

    .icon{width:16px; height:16px; opacity:.8}
    .i-thermo{fill:#ef4444}
    .i-humid{fill:#2563eb}
    .i-motion{fill:#22c55e}
    .i-water{fill:#0ea5e9}
    .i-signal{fill:#6b7280}
    a.link{color:var(--accent); text-decoration:none} a.link:hover{text-decoration:underline}
  </style>
</head>
<body>
  <header>
    <h1>Panneau Multi</h1>
    <div class="muted"><a class="link" href="/panel">ancienne version</a></div>
  </header>
  <div class="wrap"><div id="grid" class="grid"></div></div>

<!-- Мини‑набор SVG‑иконок -->
<svg style="display:none">
  <symbol id="i-thermo" viewBox="0 0 24 24"><path class="i-thermo" d="M14 14.76V5a2 2 0 1 0-4 0v9.76a4 4 0 1 0 4 0z"/></symbol>
  <symbol id="i-humid" viewBox="0 0 24 24"><path class="i-humid" d="M12 3s6 6.14 6 10a6 6 0 0 1-12 0c0-3.86 6-10 6-10z"/></symbol>
  <symbol id="i-motion" viewBox="0 0 24 24"><path class="i-motion" d="M13 5a2 2 0 1 1-2 0 2 2 0 0 1 2 0zM9 22l1-7-3 2-1-2 5-4h2l2 4-2 1-1 6H9z"/></symbol>
  <symbol id="i-water" viewBox="0 0 24 24"><path class="i-water" d="M12 3s-6 6.5-6 10.5a6 6 0 0 0 12 0C18 9.5 12 3 12 3z"/></symbol>
  <symbol id="i-signal" viewBox="0 0 24 24"><path class="i-signal" d="M3 18h2v3H3zm4-5h2v8H7zm4-4h2v12h-2zm4-5h2v17h-2z"/></symbol>
</svg>

<script>
var order = ["slot1","slot2","slot3","slot4"];
// Noms jolis pour les cartes :
var slotNames = {
  "slot1":"Garage-1",
  "slot2":"Garage-2",
  "slot3":"Maison-1",
  "slot4":"Libre"
};

function clsForTemp(t){
  if (t==null) return "";
  if (t >= 30) return "bad";
  if (t >= 26) return "warn";
  return "ok";
}
function waterBadge(w){
  if (w==null) return "";
  if (w >= 200) return '<span class="pill" style="color:#fff;background:#ef4444;border-color:transparent;">haut</span>';
  if (w >= 50)  return '<span class="pill" style="background:#fff3cd;border-color:#fde68a;">moyen</span>';
  return '<span class="pill">normal</span>';
}
function fmt(v, unit){ return (v===null || v===undefined || v==="") ? "—" : (unit ? (v+' '+unit) : v); }
function fmtBool(b){ return (b===null || b===undefined) ? "—" : (b ? "Oui" : "Non"); }

function icon(id){ return '<svg class="icon"><use href="#'+id+'"/></svg>'; }

function render(data){
  var grid = document.getElementById('grid');
  grid.innerHTML = "";
  for (var i=0;i<order.length;i++){
    var k = order[i];
    var d = data[k] || {};
    var tempClass = clsForTemp(d.temperature);

    var htmlHead = ''
      + '<div class="card-head">'
      + '  <div class="id">'+icon("i-signal")+' '+(slotNames[k])+'</div>'
      + '  <div class="time muted">'+(d.time || '')+'</div>'
      + '</div>';

    var htmlBody = ''
      + '<div class="row"><div class="label">'+icon("i-thermo")+' Température</div>'
      +   '<div class="value">'+fmt(d.temperature,'°C')
      +   ' <span class="chip '+tempClass+'"><span class="dot"></span><span class="muted">statut</span></span></div></div>'

      + '<div class="row"><div class="label">'+icon("i-humid")+' Humidité</div>'
      +   '<div class="value">'+fmt(d.humidity,'%')+'</div></div>'

      + '<div class="row"><div class="label">'+icon("i-motion")+' Mouvement</div>'
      +   '<div class="value">'+fmtBool(d.motion)+'</div></div>'

      + '<div class="row"><div class="label">'+icon("i-water")+' Eau</div>'
      +   '<div class="value">'+fmt(d.water)+' '+waterBadge(d.water)+'</div></div>';

    if (typeof d.rssi !== 'undefined'){
      htmlBody += '<div class="row"><div class="label">'+icon("i-signal")+' RSSI</div>'
                + '<div class="value">'+fmt(d.rssi)+'</div></div>';
    }
    if (typeof d.snr !== 'undefined'){
      htmlBody += '<div class="row"><div class="label">'+icon("i-signal")+' SNR</div>'
                + '<div class="value">'+fmt(d.snr)+'</div></div>';
    }

    var card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = htmlHead + '<div class="card-body">'+htmlBody+'</div>';
    grid.appendChild(card);
  }
}

async function tick(){
  try{
    var r = await fetch('/api/data_multi', {cache:'no-store'});
    var j = await r.json();
    render(j);
  }catch(e){ console.error(e); }
}
tick(); setInterval(tick, 3000);
</script>
</body>
</html>''')
