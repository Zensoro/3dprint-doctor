"""Local web interface for Print Doctor.

A minimal, self-contained web app: upload an STL/3MF, see a 3D report
with defect highlighting, and get the full analysis. Reuses the CLI
engine — this is a presentation layer, not a rewrite.

Run:
    python -m print_doctor.webapp  (then open http://127.0.0.1:8000)
"""
from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from print_doctor.mesh import analyze_mesh
from print_doctor.report import generate_report, generate_html_report
from print_doctor.visualize import generate_3d_report

app = FastAPI(title="Print Doctor", description="Local 3D printing analysis")

# session store: id -> temp dir
_sessions: dict = {}

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Print Doctor</title>
<style>
  :root { --bg:#0f1115; --panel:#171a21; --text:#d6d9de; --muted:#7a8090;
          --accent:#4cd964; }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:var(--bg); color:var(--text); min-height:100vh;
         font-family: -apple-system, "Segoe UI", Roboto, sans-serif; }
  header { padding:24px 32px; border-bottom:1px solid #22262f;
           display:flex; align-items:baseline; gap:16px; }
  header h1 { font-size:18px; letter-spacing:.1em; color:#fff; }
  header .tag { color:var(--muted); font-size:12px; }
  main { max-width:720px; margin:0 auto; padding:48px 24px; }
  .drop { border:2px dashed #333a46; border-radius:12px; padding:64px 32px;
          text-align:center; cursor:pointer; transition:.2s; }
  .drop:hover, .drop.drag { border-color:var(--accent); background:#12161d; }
  .drop .icon { font-size:40px; margin-bottom:12px; }
  .drop p { color:var(--muted); font-size:14px; }
  .drop .sub { font-size:12px; color:#4a5161; margin-top:8px; }
  #status { margin-top:20px; text-align:center; color:var(--muted); font-size:13px; }
  .features { margin-top:48px; display:grid; grid-template-columns:repeat(3,1fr);
              gap:12px; }
  .feat { background:var(--panel); border:1px solid #22262f; border-radius:8px;
          padding:16px; }
  .feat h3 { font-size:13px; color:#fff; margin-bottom:6px; }
  .feat p { font-size:11px; color:var(--muted); line-height:1.5; }
  .feat a { color:var(--accent); text-decoration:none; font-size:11px; }
  input[type=file] { display:none; }
</style>
</head>
<body>
<header><h1>PRINT DOCTOR</h1><span class="tag">local · private · offline</span></header>
<main>
  <div class="drop" id="drop">
    <div class="icon">🖨️</div>
    <p>Drop an STL or 3MF here, or click to choose</p>
    <p class="sub">analysis runs locally — your model never leaves this machine</p>
    <input type="file" id="file" accept=".stl,.3mf">
  </div>
  <div id="status"></div>

  <div class="features">
    <div class="feat"><h3>Printability</h3>
      <p>8 checks, 0-100 score, defect highlighting in 3D</p>
      <a href="#" onclick="about()">how it works</a></div>
    <div class="feat"><h3>Cost</h3>
      <p>material, electricity, machine, labor, supports</p></div>
    <div class="feat"><h3>Tools</h3>
      <p>orientation, hollowing, repair, G-code analysis</p></div>
  </div>
</main>
<script>
const drop = document.getElementById('drop');
const input = document.getElementById('file');
const status = document.getElementById('status');
drop.addEventListener('click', () => input.click());
drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('drag'); });
drop.addEventListener('dragleave', () => drop.classList.remove('drag'));
drop.addEventListener('drop', e => { e.preventDefault(); drop.classList.remove('drag');
  if (e.dataTransfer.files.length) upload(e.dataTransfer.files[0]); });
input.addEventListener('change', () => { if (input.files.length) upload(input.files[0]); });

async function upload(file) {
  status.textContent = 'analyzing ' + file.name + ' ...';
  const fd = new FormData();
  fd.append('file', file);
  try {
    const r = await fetch('/analyze', { method: 'POST', body: fd });
    const j = await r.json();
    if (j.error) { status.textContent = 'error: ' + j.error; return; }
    window.location.href = '/view/' + j.id;
  } catch(e) { status.textContent = 'error: ' + e; }
}
function about() { status.textContent = 'see docs at github.com/Zensoro/3dprint-doctor'; }
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return INDEX_HTML


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    session_id = uuid.uuid4().hex
    tmpdir = Path(tempfile.mkdtemp(prefix="pd_"))
    ext = Path(file.filename or "model.stl").suffix or ".stl"
    src = tmpdir / f"model{ext}"
    data = await file.read()
    src.write_bytes(data)

    try:
        analysis = analyze_mesh(str(src))
    except Exception as e:
        return JSONResponse({"error": str(e)})

    # 3D report
    report_3d = tmpdir / "report_3d.html"
    generate_3d_report(str(src), str(report_3d), analysis)

    # text report
    text_report = generate_report(analysis)
    html_report = generate_html_report(analysis)

    _sessions[session_id] = {
        "dir": tmpdir,
        "filename": file.filename,
        "score": analysis.score,
        "issues": [{"name": i.name, "severity": i.severity.value,
                    "description": i.description, "suggestion": i.suggestion}
                   for i in analysis.issues],
        "mesh": {"watertight": analysis.is_watertight,
                 "manifold": analysis.is_manifold,
                 "triangles": analysis.triangle_count,
                 "volume_cm3": round(analysis.volume / 1000.0, 2)},
        "text_report": text_report,
        "html_report": html_report,
    }
    return {"id": session_id, "filename": file.filename,
            "score": analysis.score, "issue_count": len(analysis.issues)}


@app.get("/view/{session_id}", response_class=HTMLResponse)
async def view(session_id: str):
    if session_id not in _sessions:
        return HTMLResponse("<h3>session not found — upload again</h3>")
    sess = _sessions[session_id]
    report_3d = sess["dir"] / "report_3d.html"
    html = report_3d.read_text() if report_3d.exists() else "<h3>no 3D report</h3>"
    return html


@app.get("/report/{session_id}", response_class=HTMLResponse)
async def report(session_id: str):
    if session_id not in _sessions:
        return HTMLResponse("<h3>not found</h3>")
    sess = _sessions[session_id]
    return HTMLResponse(sess["text_report"].replace("\n", "<br>"))


@app.get("/api/report/{session_id}")
async def api_report(session_id: str):
    if session_id not in _sessions:
        return JSONResponse({"error": "not found"})
    sess = _sessions[session_id]
    return JSONResponse({
        "filename": sess["filename"], "score": sess["score"],
        "issues": sess["issues"], "mesh": sess["mesh"],
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
