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
      --card:#ffffff; --border:#e5e7eb; --shadow:0 8px 20px rgba(0,0,0,.06);
      --ok:#16a34a; --warn:#f59e0b; --bad:#ef4444; --accent:#2563eb;
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

    /* 2×2 sur desktop, 1 colonne sur mobile */
    .grid{display:grid; gap:16px; grid-template-columns: repeat(2, minmax(280px, 1fr))}
    @media (max-width: 840px){ .grid{grid-template-columns: 1fr} }

    .card{
      background:var(--card); border:1px solid var(--border); border-radius:16px;
      box-shadow:var(--shadow); padding:16px 16px 14px
    }
    .top{display:flex; align-items:baseline; justify-content:space-between; margin-bottom:6px}
    .id{font-weight:700; font-size:16px}
    .time{opacity:.7}
    .row{display:flex; justify-content:space-between; padding:6px 0; border-top:1px dashed var(--border)}
    .row:first-of-type{border-top:none}
    .label{opacity:.85}
    .value{font-weight:600}
    .chip{display:inline-flex; align-items:center; gap:6px; padding:2px 8px; border-radius:999px;
      border:1px solid var(--border); font-size:12px; color:var(--muted); background:#fafafa}
    .dot{width:8px; height:8px; border-radius:50%}
    .ok  .dot{background:var(--ok)}
    .warn .dot{background:var(--warn)}
    .bad .dot{background:var(--bad)}
    .pill{display:inline-block; padding:0 8px; border-radius:999px; border:1px solid var(--border);
      margin-left:8px; font-size:12px; color:var(--muted); background:#f8fafc}
    a.link{color:var(--accent); text-decoration:none} a.link:hover{text-decoration:underline}
  </style>
</head>
<body>
  <header>
    <h1>Panneau Multi</h1>
    <div class="muted"><a class="link" href="/panel">ancienne version</a></div>
  </header>
  <div class="wrap"><div id="grid" class="grid"></div></div>

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

function render(data){
  var grid = document.getElementById('grid');
  grid.innerHTML = "";
  for (var i=0;i<order.length;i++){
    var k = order[i];
    var d = data[k] || {};
    var tempClass = clsForTemp(d.temperature);

    var html = '';
    html += '<div class="top">';
    html += '  <div class="id">'+(slotNames[k])+'</div>';
    html += '  <div class="time muted">'+(d.time || '')+'</div>';
    html += '</div>';

    html += '<div class="row"><div class="label">Température</div><div class="value">'+fmt(d.temperature,'°C')+
            ' <span class="chip '+tempClass+'"><span class="dot"></span><span class="muted">statut</span></span></div></div>';

    html += '<div class="row"><div class="label">Humidité</div><div class="value">'+fmt(d.humidity,'%')+'</div></div>';
    html += '<div class="row"><div class="label">Mouvement</div><div class="value">'+fmtBool(d.motion)+'</div></div>';
    html += '<div class="row"><div class="label">Eau</div><div class="value">'+fmt(d.water)+ ' ' + waterBadge(d.water)+'</div></div>';

    if (typeof d.rssi !== 'undefined'){
      html += '<div class="row"><div class="label">RSSI</div><div class="value">'+fmt(d.rssi)+'</div></div>';
    }
    if (typeof d.snr !== 'undefined'){
      html += '<div class="row"><div class="label">SNR</div><div class="value">'+fmt(d.snr)+'</div></div>';
    }

    var card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = html;
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
