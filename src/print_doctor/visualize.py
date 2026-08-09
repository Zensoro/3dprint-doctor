"""Generate an interactive 3D HTML report with defect highlighting.

Loads a mesh, recomputes defect face indices (reusing the detector
logic), and emits a single self-contained HTML file with three.js
embedded (no network needed to view). Defect faces are colored by
type; the model can be rotated/zoomed; clicking a defect in the list
centers the camera on it.

Usage:
    from print_doctor.visualize import generate_3d_report
    generate_3d_report("model.stl", "report.html", analysis)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import trimesh

from print_doctor.models import MeshAnalysis

THREE_JS_PATH = (
    Path(__file__).resolve().parent / "assets" / "three.min.js"
)

# defect type -> (color, label)
DEFECT_COLORS = {
    "overhang": ("#ff5252", "Overhang"),
    "thin_wall": ("#ffd740", "Thin wall"),
    "self_intersection": ("#e040fb", "Self-intersection"),
    "non_watertight": ("#40c4ff", "Non-watertight"),
    "non_manifold": ("#ff6e40", "Non-manifold"),
    "isolated_faces": ("#69f0ae", "Isolated"),
}


def _overhang_faces(mesh: trimesh.Trimesh, max_angle: float = 45.0) -> np.ndarray:
    nz = mesh.face_normals[:, 2]
    downward = nz < 0
    if not np.any(downward):
        return np.array([], dtype=int)
    angles = np.degrees(np.arccos(np.clip(-nz[downward], 0.0, 1.0)))
    idx = np.where(downward)[0]
    return idx[angles < max_angle]


def _thin_wall_faces(
    mesh: trimesh.Trimesh, min_thickness: float = 0.8, sample_count: int = 500
) -> np.ndarray:
    """Faces near thin-wall sample points (ray cast inward)."""
    points, face_indices = trimesh.sample.sample_surface(mesh, sample_count)
    normals = mesh.face_normals[face_indices]
    origins = points - normals * 1e-4
    locations, ray_idx, _ = mesh.ray.intersects_location(origins, -normals)
    if len(locations) == 0:
        return np.array([], dtype=int)
    dist = np.linalg.norm(locations - origins[ray_idx], axis=1)
    thin = dist < min_thickness
    return np.unique(face_indices[ray_idx[thin]]) if np.any(thin) else np.array([], dtype=int)


def _self_intersection_faces(mesh: trimesh.Trimesh) -> np.ndarray:
    from print_doctor.mesh import detect_self_intersections, _triangles_intersect

    tris = mesh.triangles
    faces = mesh.faces
    n = len(tris)
    mins = tris.min(axis=1)
    maxs = tris.max(axis=1)
    tree = mesh.triangles_tree
    found = set()
    for i in range(n):
        q = (float(mins[i][0]), float(mins[i][1]), float(mins[i][2]),
             float(maxs[i][0]), float(maxs[i][1]), float(maxs[i][2]))
        for j in tree.intersection(q):
            j = int(j)
            if j <= i:
                continue
            if len(set(faces[i]) & set(faces[j])) > 0:
                continue
            if _triangles_intersect(tris[i], tris[j]):
                found.add(i)
                found.add(j)
    return np.array(sorted(found), dtype=int)


def compute_defect_faces(mesh: trimesh.Trimesh) -> Dict[str, np.ndarray]:
    """Recompute defect face indices for visualization."""
    result = {}
    if mesh.is_watertight:
        result["self_intersection"] = _self_intersection_faces(mesh)
    result["overhang"] = _overhang_faces(mesh)
    result["thin_wall"] = _thin_wall_faces(mesh)
    return {k: v for k, v in result.items() if len(v) > 0}


def generate_3d_report(
    model_path: str,
    output_path: str,
    analysis: Optional[MeshAnalysis] = None,
) -> str:
    """Generate a self-contained interactive 3D HTML report.

    Args:
        model_path: STL/3MF file
        output_path: output HTML path
        analysis: optional pre-computed MeshAnalysis (for score/issues)

    Returns:
        Output path
    """
    from print_doctor.mesh import load_mesh

    mesh = load_mesh(model_path)
    vertices = mesh.vertices.astype(np.float64)
    faces = mesh.faces.astype(np.int32)

    # center + normalize for good camera framing
    center = vertices.mean(axis=0)
    vertices = vertices - center
    scale = np.max(np.abs(vertices)) if len(vertices) else 1.0
    vertices = vertices / max(scale, 1e-9)

    defect_faces = compute_defect_faces(mesh)

    # per-face colors: index into DEFECT_COLORS, default gray
    face_colors = np.zeros((len(faces), 3), dtype=np.float32)
    face_colors[:] = (0.75, 0.76, 0.78)  # neutral gray
    legend = []
    for kind, idx in defect_faces.items():
        if kind not in DEFECT_COLORS:
            continue
        hex_color, label = DEFECT_COLORS[kind]
        rgb = tuple(int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
        face_colors[idx] = rgb
        legend.append({"kind": kind, "label": label,
                       "color": hex_color, "count": int(len(idx))})

    # issue text (from analysis if given)
    issues_text = []
    if analysis:
        for i in analysis.issues:
            issues_text.append({
                "severity": i.severity.value,
                "name": i.name,
                "description": i.description,
                "suggestion": i.suggestion,
            })

    three_js = ""
    if THREE_JS_PATH.exists():
        three_js = THREE_JS_PATH.read_text()
    else:
        three_js = "// three.js not found at build time"

    data = {
        "vertices": vertices.tolist(),
        "faces": faces.tolist(),
        "faceColors": face_colors.tolist(),
        "legend": legend,
        "issues": issues_text,
        "score": analysis.score if analysis else None,
        "filename": Path(model_path).name,
    }

    html = _HTML_TEMPLATE.replace("__THREE_JS__", three_js) \
                          .replace("__DATA__", json.dumps(data))
    Path(output_path).write_text(html)
    return output_path


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Print Doctor 3D Report</title>
<style>
  :root { --bg: #0f1115; --panel: #171a21; --text: #d6d9de; --muted: #7a8090; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: var(--bg); color: var(--text);
         font-family: "SF Mono", Menlo, Consolas, monospace; }
  #viewer { position: fixed; inset: 0; }
  .panel { position: fixed; background: rgba(23,26,33,.92); border: 1px solid #262b36;
           border-radius: 8px; padding: 14px 16px; backdrop-filter: blur(6px); }
  #top { top: 14px; left: 14px; right: 14px; display: flex; gap: 12px; align-items: baseline; }
  #top h1 { font-size: 13px; letter-spacing: .08em; color: #fff; font-weight: 600; }
  #top .meta { font-size: 11px; color: var(--muted); }
  #score { margin-left: auto; font-size: 15px; }
  #score .val { color: #4cd964; font-weight: 700; }
  #legend { bottom: 14px; left: 14px; max-width: 260px; font-size: 11px; }
  #legend h3 { font-size: 10px; letter-spacing: .12em; color: var(--muted); margin-bottom: 8px; }
  .lg-row { display: flex; align-items: center; gap: 8px; padding: 3px 0; }
  .lg-dot { width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; }
  .lg-count { margin-left: auto; color: var(--muted); }
  #issues { right: 14px; bottom: 14px; max-width: 320px; max-height: 40vh; overflow-y: auto; font-size: 11px; }
  #issues h3 { font-size: 10px; letter-spacing: .12em; color: var(--muted); margin-bottom: 8px; }
  .iss { border-left: 2px solid #444; padding: 4px 8px; margin: 4px 0; }
  .iss.err { border-color: #ff5252; } .iss.warn { border-color: #ffd740; } .iss.info { border-color: #40c4ff; }
  .iss .n { font-weight: 700; } .iss .d { color: var(--muted); margin-top: 2px; }
  #hint { bottom: 14px; left: 50%; transform: translateX(-50%); font-size: 10px; color: var(--muted); }
</style>
</head>
<body>
<div id="viewer"></div>
<div class="panel" id="top">
  <h1>PRINT DOCTOR</h1>
  <span class="meta" id="fname"></span>
  <span id="score"></span>
</div>
<div class="panel" id="legend"><h3>DEFECTS</h3><div id="lg"></div></div>
<div class="panel" id="issues"><h3>ISSUES</h3><div id="iss"></div></div>
<div class="panel" id="hint">drag to rotate · scroll to zoom</div>

<script>
__THREE_JS__
</script>
<script>
const DATA = __DATA__;
</script>
<script>
// WebGL support check with graceful degradation
function webglOk() {
  try {
    const c = document.createElement('canvas');
    return !!(window.WebGLRenderingContext &&
      (c.getContext('webgl') || c.getContext('experimental-webgl')));
  } catch (e) { return false; }
}
if (!webglOk()) {
  document.getElementById('viewer').innerHTML =
    '<div style="position:absolute;inset:0;display:flex;align-items:center;' +
    'justify-content:center;color:var(--muted);font-size:13px;">' +
    'WebGL is not available in this browser — open this file in Chrome, ' +
    'Firefox or Edge to see the 3D model.</div>';
  throw new Error('WebGL unavailable');
}
</script>
<script>
// ---- scene ----
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0f1115);
const camera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, 0.01, 100);
camera.position.set(2.4, 1.8, 3.0);
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(innerWidth, innerHeight);
renderer.setPixelRatio(devicePixelRatio);
document.getElementById('viewer').appendChild(renderer.domElement);

// lights
scene.add(new THREE.HemisphereLight(0xffffff, 0x22242c, 1.1));
const dir = new THREE.DirectionalLight(0xffffff, 0.9);
dir.position.set(3, 5, 2);
scene.add(dir);

// geometry
const geo = new THREE.BufferGeometry();
geo.setAttribute('position',
  new THREE.Float32BufferAttribute(DATA.vertices.flat(), 3));
geo.setIndex(DATA.faces.flat());
const colors = new Float32Array(DATA.faceColors.flat());
geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
geo.computeVertexNormals();

const mat = new THREE.MeshStandardMaterial({
  vertexColors: true, metalness: .25, roughness: .55, side: THREE.DoubleSide,
});
const mesh = new THREE.Mesh(geo, mat);
scene.add(mesh);

// wireframe overlay for technical feel
const wire = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({
  wireframe: true, color: 0x000000, transparent: true, opacity: .06,
}));
scene.add(wire);

// orbit controls (minimal manual implementation to avoid extra imports)
let dragging = false, lastX = 0, lastY = 0, theta = 0.6, phi = 1.0, radius = 4.0;
const target = new THREE.Vector3(0, 0, 0);
function updateCamera() {
  camera.position.x = radius * Math.sin(phi) * Math.cos(theta);
  camera.position.y = radius * Math.cos(phi);
  camera.position.z = radius * Math.sin(phi) * Math.sin(theta);
  camera.lookAt(target);
}
renderer.domElement.addEventListener('pointerdown', e => {
  dragging = true; lastX = e.clientX; lastY = e.clientY;
});
addEventListener('pointermove', e => {
  if (!dragging) return;
  theta -= (e.clientX - lastX) * 0.01;
  phi = Math.max(0.1, Math.min(Math.PI - 0.1, phi - (e.clientY - lastY) * 0.01));
  lastX = e.clientX; lastY = e.clientY;
  updateCamera();
});
addEventListener('pointerup', () => dragging = false);
addEventListener('wheel', e => {
  radius = Math.max(1.5, Math.min(12, radius + e.deltaY * 0.005));
  updateCamera();
});
addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});
updateCamera();

// UI
document.getElementById('fname').textContent = DATA.filename;
if (DATA.score !== null) {
  const cls = DATA.score >= 80 ? '#4cd964' : DATA.score >= 60 ? '#ffd740' : '#ff5252';
  document.getElementById('score').innerHTML =
    `score <span class="val" style="color:${cls}">${DATA.score.toFixed(1)}</span>/100`;
}
const lg = document.getElementById('lg');
if (DATA.legend.length === 0) lg.innerHTML = '<div style="color:var(--muted)">no defects found</div>';
else DATA.legend.forEach(l => {
  const row = document.createElement('div'); row.className = 'lg-row';
  row.innerHTML = `<span class="lg-dot" style="background:${l.color}"></span>${l.label}
                   <span class="lg-count">${l.count}</span>`;
  lg.appendChild(row);
});
const iss = document.getElementById('iss');
if (DATA.issues.length === 0) iss.innerHTML = '<div style="color:var(--muted)">no issues</div>';
else DATA.issues.forEach(i => {
  const d = document.createElement('div');
  d.className = 'iss ' + i.severity;
  d.innerHTML = `<div class="n">${i.severity.toUpperCase()} · ${i.name}</div>
                 <div class="d">${i.description}</div>`;
  iss.appendChild(d);
});

function animate() { requestAnimationFrame(animate); renderer.render(scene, camera); }
animate();
</script>
</body>
</html>
"""
