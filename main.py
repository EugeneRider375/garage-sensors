@app.get("/panel_multi", response_class=HTMLResponse)
async def panel_multi(request: Request):
    if request.cookies.get("auth") != "true":
        return RedirectResponse(url="/")
    return HTMLResponse("""
<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Garage Panel – Multi</title>
  <style>
    :root{
      --bg:#ffffff;
      --fg:#111111;
      --muted:#6b7280;
      --card:#ffffff;
      --border:#e5e7eb;
      --shadow:0 8px 20px rgba(0,0,0,.06);
      --ok:#16a34a;        /* зелёный мягкий */
      --warn:#f59e0b;      /* янтарный */
      --bad:#ef4444;       /* красный */
      --accent:#2563eb;    /* синий для заголовков/ссылок */
    }
    *{box-sizing:border-box}
    html,body{height:100%}
    body{
      margin:0; background:var(--bg); color:var(--fg);
      font:14px/1.5 system-ui,-apple-system,Segoe UI,Roboto,Arial;
    }
    header{
      position:sticky; top:0; z-index:10;
      background:linear-gradient(#fff,rgba(255,255,255,.92));
      backdrop-filter:saturate(1.2) blur(2px);
      border-bottom:1px solid var(--border);
      padding:14px 18px;
      display:flex; align-items:center; justify-content:space-between;
    }
    h1{margin:0; font-size:18px; font-weight:650;}
    .muted{color:var(--muted)}
    .wrap{max-width:1100px; margin:0 auto; padding:18px;}
    /* 2×2 сетка на десктопе, 1 колонка на мобильном */
    .grid{
      display:grid; gap:16px;
      grid-template-columns: repeat(2, minmax(280px, 1fr));
    }
    @media (max-width: 840px){
      .grid{grid-template-columns: 1fr;}
    }
    .card{
      background:var(--card);
      border:1px solid var(--border);
      border-radius:16px;
      box-shadow:var(--shadow);
      padding:16px 16px 14px;
    }
    .top{
      display:flex; align-items:baseline; justify-content:space-between; margin-bottom:6px;
    }
    .id{font-weight:700; font-size:16px;}
    .time{font-variant-numeric:tabular-nums}
    .row{display:flex; justify-content:space-between; padding:6px 0; border-top:1px dashed var(--border);}
    .row:first-of-type{border-top:none}
    .label{opacity:.85}
    .value{font-weight:600}
    .chip{
      display:inline-flex; align-items:center; gap:6px;
      padding:2px 8px; border-radius:999px; border:1px solid var(--border);
      font-size:12px; color:var(--muted); background:#fafafa;
    }
    .dot{width:8px; height:8px; border-radius:50%;}
    .ok  .dot{background:var(--ok)}
    .warn.dot{background:var(--warn)}
    .bad .dot{background:var(--bad)}
    /* мягкая цветная метка рядом со значением воды */
    .pill{
      display:inline-block; padding:0 8px; border-radius:999px; border:1px solid var(--border);
      margin-left:8px; font-size:12px; color:var(--muted); background:#f8fafc;
    }
    a.link{color:var(--accent); text-decoration:none}
    a.link:hover{text-decoration:underline}
  </style>
</head>
<body>
  <header>
    <h1>Garage Panel — Multi</h1>
    <div class="muted"><a class="link" href="/panel">классическая панель</a></div>
  </header>

  <div class="wrap">
    <div id="grid" class="grid"></div>
  </div>

<script>
const order = ["slot1","slot2","slot3","slot4"];

function clsForTemp(t){
  if (t==null) return "";
  if (t >= 30) return "bad";
  if (t >= 26) return "warn";
  return "ok";
}
function waterBadge(w){
  if (w==null) return "";
  if (w >= 200) return '<span class="pill" style="color:#fff;background:var(--bad);border-color:transparent;">высоко</span>';
  if (w >= 50)  return '<span class="pill" style="background:#fff3cd;border-color:#fde68a;">средне</span>';
  return '<span class="pill">норма</span>';
}
function fmt(v, unit=""){ return (v===null || v===undefined || v==="") ? "—" : (unit ? v+" "+unit : v); }
function fmtBool(b){ return (b===null || b===undefined) ? "—" : (b ? "Да" : "Нет"); }

function render(data){
  const grid = document.getElementById('grid');
  grid.innerHTML = "";
  order.forEach(k=>{
    const d = data[k] || {};
    const tempClass = clsForTemp(d.temperature);
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <div class="top">
        <div class="id">${d.deviceId || k}</div>
        <div class="time muted">${d.time || ""}</div>
      </div>

      <div class="row">
        <div class="label">Темп.</div>
        <div class="value">
          ${fmt(d.temperature, "°C")}
          <span class="chip ${tempClass}">
            <span class="dot"></span>
            <span class="muted">статус</span>
          </span>
        </div>
      </div>

      <div class="row">
        <div class="label">Влажн.</div>
        <div class="value">${fmt(d.humidity, "%")}</div>
      </div>

      <div class="row">
        <div class="label">Движение</div>
        <div class="value">${fmtBool(d.motion)}</div>
      </div>

      <div class="row">
        <div class="label">Вода</div>
        <div class="value">${fmt(d.water)} ${waterBadge(d.water)}</div>
      </div>

      ${ (d.rssi!==undefined) ? `
      <div class="row">
        <div class="label">RSSI</div>
        <div class="value">${fmt(d.rssi)}</div>
      </div>` : "" }

      ${ (d.snr!==undefined) ? `
      <div class="row">
        <div class="label">SNR</div>
        <div class="value">${fmt(d.snr)}</div>
      </div>` : "" }
    `;
    grid.appendChild(card);
  });
}

async function tick(){
  try{
    const r = await fetch('/api/data_multi', {cache:'no-store'});
    const j = await r.json();
    render(j);
  }catch(e){
    console.error(e);
  }
}
tick();
setInterval(tick, 3000);
</script>
</body>
</html>
    """)
