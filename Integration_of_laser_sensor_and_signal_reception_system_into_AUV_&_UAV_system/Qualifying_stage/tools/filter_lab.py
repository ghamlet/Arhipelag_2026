#!/usr/bin/env python3
"""Filter Lab — interactive web UI for testing underwater image filters.

Auto-discovers apply_* functions from generate_dataset.py and provides
a browser-based interface with real-time split-view preview (original vs filtered).

Usage:
    python tools/filter_lab.py
    Then open http://localhost:5000
"""
import os
import sys
import inspect
import importlib.util
import io
import json
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
GENERATE_PY = os.path.join(TOOLS_DIR, "generate_dataset.py")

generate_module = None


def load_generate_module():
    global generate_module
    spec = importlib.util.spec_from_file_location("generate_dataset", GENERATE_PY)
    generate_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generate_module)


def get_apply_functions():
    load_generate_module()
    funcs = {}
    for name, obj in inspect.getmembers(generate_module, inspect.isfunction):
        if name.startswith("apply_"):
            sig = inspect.signature(obj)
            params = {}
            for pname, param in sig.parameters.items():
                if pname == "img":
                    continue
                params[pname] = {
                    "default": param.default if param.default is not inspect.Parameter.empty else None,
                    "annotation": str(param.annotation) if param.annotation is not inspect.Parameter.empty else "",
                }
            funcs[name] = {
                "doc": inspect.getdoc(obj) or "",
                "params": params,
            }
    return funcs


@app.route("/")
def index():
    return INDEX_HTML


@app.route("/api/functions")
def api_functions():
    return jsonify(get_apply_functions())


@app.route("/api/apply", methods=["POST"])
def api_apply():
    from PIL import Image

    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    img = Image.open(file.stream).convert("RGB")

    load_generate_module()

    filters_json = request.form.get("filters", "{}")
    filters = json.loads(filters_json)

    for func_name, params in filters.items():
        func = getattr(generate_module, func_name, None)
        if func is None or not callable(func):
            continue
        sig = inspect.signature(func)
        call_args = {"img": img}
        for pname, pval in params.items():
            if pname in sig.parameters:
                param = sig.parameters[pname]
                if pval is not None and pval != "":
                    call_args[pname] = float(pval)
                elif param.default is not None:
                    call_args[pname] = param.default
        img = func(**call_args)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


INDEX_HTML = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Filter Lab</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter','Segoe UI',system-ui,sans-serif;background:#0a0a0f;color:#e0e0e0;height:100vh;display:flex;flex-direction:column;overflow:hidden}
header{background:linear-gradient(135deg,#12121a,#1a1a2e);padding:10px 20px;border-bottom:1px solid #2a2a3a;display:flex;align-items:center;gap:12px;flex-shrink:0}
header h1{font-size:16px;font-weight:700;background:linear-gradient(135deg,#60a5fa,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.btn{background:linear-gradient(135deg,#3b82f6,#2563eb);color:#fff;border:none;padding:7px 14px;border-radius:8px;cursor:pointer;font-size:12px;font-weight:600;transition:all .2s}
.btn:hover{transform:translateY(-1px);box-shadow:0 4px 12px rgba(59,130,246,.4)}
.btn:active{transform:translateY(0)}
.btn-secondary{background:#1e1e2e;border:1px solid #2a2a3a}
.btn-secondary:hover{background:#2a2a3a;box-shadow:none}
.main{display:flex;flex:1;overflow:hidden}
.sidebar{width:280px;background:#111118;border-right:1px solid #1e1e2e;overflow-y:auto;padding:12px;flex-shrink:0;display:flex;flex-direction:column;gap:8px}
.sidebar::-webkit-scrollbar{width:4px}
.sidebar::-webkit-scrollbar-track{background:transparent}
.sidebar::-webkit-scrollbar-thumb{background:#333;border-radius:4px}
.preview{flex:1;display:flex;gap:2px;padding:8px;overflow:hidden;background:#08080c}
.preview-pane{flex:1;display:flex;align-items:center;justify-content:center;position:relative;border-radius:10px;overflow:hidden;background:#0d0d14;border:1px solid #1a1a28}
.preview-pane img{max-width:100%;max-height:100%;object-fit:contain}
.preview-label{position:absolute;top:8px;left:10px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:1px;color:#666;background:rgba(10,10,15,.8);padding:3px 8px;border-radius:4px}
.preview .placeholder{color:#333;font-size:13px;text-align:center;padding:20px}
.filter-group{background:#13131d;border:1px solid #1e1e2e;border-radius:8px;overflow:hidden;transition:border-color .2s}
.filter-group:hover{border-color:#2a2a3a}
.filter-header{display:flex;align-items:center;padding:8px 10px;gap:8px;cursor:pointer}
.filter-header:hover{background:#1a1a28}
.filter-header input[type="checkbox"]{width:14px;height:14px;accent-color:#3b82f6;cursor:pointer}
.filter-header label{font-size:11px;font-weight:600;cursor:pointer;flex:1;text-transform:capitalize}
.filter-header .doc{font-size:9px;color:#555;margin-top:1px;line-height:1.3}
.filter-body{padding:4px 10px 8px;display:none}
.filter-body.open{display:block}
.slider-row{display:flex;align-items:center;gap:6px;margin-top:4px}
.slider-row label{font-size:10px;color:#666;min-width:40px}
.slider-row input[type="range"]{-webkit-appearance:none;flex:1;height:4px;background:#1e1e2e;border-radius:4px;outline:none;cursor:pointer}
.slider-row input[type="range"]::-webkit-slider-thumb{-webkit-appearance:none;width:14px;height:14px;background:linear-gradient(135deg,#3b82f6,#2563eb);border-radius:50%;cursor:pointer;box-shadow:0 2px 6px rgba(59,130,246,.4);transition:transform .15s}
.slider-row input[type="range"]::-webkit-slider-thumb:hover{transform:scale(1.2)}
.slider-row input[type="range"]::-moz-range-thumb{width:14px;height:14px;background:linear-gradient(135deg,#3b82f6,#2563eb);border-radius:50%;cursor:pointer;border:none}
.slider-row .val{font-size:10px;color:#3b82f6;min-width:32px;text-align:right;font-family:'JetBrains Mono',monospace}
.spinner{position:absolute;width:32px;height:32px;border:2px solid #1e1e2e;border-top-color:#3b82f6;border-radius:50%;animation:spin .7s linear infinite;display:none}
.spinner.active{display:block}
@keyframes spin{to{transform:rotate(360deg)}}
.status{font-size:10px;color:#555;margin-top:auto;padding:8px;background:#0d0d14;border-radius:6px;text-align:center;border:1px solid #1a1a28}
</style>
</head>
<body>
<header>
  <h1>Filter Lab</h1>
  <input type="file" id="fileInput" accept="image/*" style="display:none">
  <button class="btn" onclick="document.getElementById('fileInput').click()">Load Image</button>
  <button class="btn btn-secondary" onclick="resetFilters()">Reset</button>
</header>
<div class="main">
  <div class="sidebar">
    <div id="filtersList"></div>
    <div class="status" id="status">Load an image to start</div>
  </div>
  <div class="preview">
    <div class="preview-pane">
      <span class="preview-label">Original</span>
      <img id="originalImg" style="display:none">
      <div class="placeholder" id="placeholder">Drop or select an image</div>
    </div>
    <div class="preview-pane">
      <span class="preview-label">Result</span>
      <div class="spinner" id="spinner"></div>
      <img id="resultImg" style="display:none">
    </div>
  </div>
</div>
<script>
let functionsData = {};
let currentFile = null;
let debounceTimer = null;
let originalUrl = null;

const SLIDER_CONFIG = {
  apply_illumination: {min:0.5,max:1.3,step:0.01},
  apply_turbidity: {min:0,max:5,step:0.1},
  apply_glare: {min:0,max:6,step:1},
  apply_particles: {min:0,max:3,step:0.05},
  apply_blue_filter: {min:0,max:1,step:0.02},
  apply_green_filter: {min:0,max:1,step:0.02}
};

async function init() {
  const resp = await fetch('/api/functions');
  functionsData = await resp.json();
  renderFilters();
}

function renderFilters() {
  const container = document.getElementById('filtersList');
  container.innerHTML = '';
  for (const [name, info] of Object.entries(functionsData)) {
    const displayName = name.replace('apply_','').replace(/_/g,' ');
    const group = document.createElement('div');
    group.className = 'filter-group';
    group.dataset.func = name;

    const hasParams = Object.keys(info.params).length > 0;
    let bodyHtml = '';
    if (hasParams) {
      for (const [pname, pinfo] of Object.entries(info.params)) {
        const cfg = SLIDER_CONFIG[name] || {min:0,max:1,step:0.05};
        const def = pinfo.default ?? cfg.min;
        bodyHtml += `
          <div class="slider-row">
            <label>${pname}</label>
            <input type="range" min="${cfg.min}" max="${cfg.max}" step="${cfg.step}" value="${def}"
                   data-func="${name}" data-param="${pname}" oninput="onSlider(this)">
            <span class="val">${Number(def).toFixed(2)}</span>
          </div>`;
      }
    }

    group.innerHTML = `
      <div class="filter-header" onclick="toggleFilter(this)">
        <input type="checkbox" id="cb_${name}" data-func="${name}" onchange="onToggle(this)">
        <div>
          <label for="cb_${name}">${displayName}</label>
          <div class="doc">${info.doc.split('\n')[0]}</div>
        </div>
      </div>
      <div class="filter-body">${bodyHtml}</div>`;
    container.appendChild(group);
  }
}

function toggleFilter(header) {
  header.nextElementSibling.classList.toggle('open');
}

function onToggle(cb) {
  if (cb.checked) cb.closest('.filter-group').querySelector('.filter-body').classList.add('open');
  scheduleRender();
}

function onSlider(input) {
  const step = parseFloat(input.step);
  input.nextElementSibling.textContent = step < 0.1 ? parseFloat(input.value).toFixed(2) : parseFloat(input.value).toFixed(step < 1 ? 1 : 0);
  scheduleRender();
}

function scheduleRender() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(renderImage, 120);
}

async function renderImage() {
  if (!currentFile) return;
  const spinner = document.getElementById('spinner');
  const img = document.getElementById('resultImg');
  const status = document.getElementById('status');

  const filters = {};
  document.querySelectorAll('.filter-group').forEach(group => {
    const funcName = group.dataset.func;
    const cb = group.querySelector('input[type="checkbox"]');
    if (!cb.checked) return;
    const params = {};
    group.querySelectorAll('input[type="range"]').forEach(slider => {
      params[slider.dataset.param] = parseFloat(slider.value);
    });
    filters[funcName] = params;
  });

  if (Object.keys(filters).length === 0) {
    img.style.display = 'none';
    status.textContent = 'No filters selected';
    return;
  }

  spinner.classList.add('active');
  status.textContent = 'Rendering...';

  const formData = new FormData();
  formData.append('image', currentFile);
  formData.append('filters', JSON.stringify(filters));

  try {
    const resp = await fetch('/api/apply', { method: 'POST', body: formData });
    if (!resp.ok) throw new Error('Server error');
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    if (originalUrl) URL.revokeObjectURL(originalUrl);
    img.onload = () => { URL.revokeObjectURL(url); };
    img.src = url;
    img.style.display = 'block';
    status.textContent = `Applied ${Object.keys(filters).length} filter(s)`;
  } catch (e) {
    status.textContent = 'Error: ' + e.message;
  } finally {
    spinner.classList.remove('active');
  }
}

function resetFilters() {
  document.querySelectorAll('.filter-group input[type="checkbox"]').forEach(cb => cb.checked = false);
  document.querySelectorAll('.filter-body').forEach(b => b.classList.remove('open'));
  document.querySelectorAll('input[type="range"]').forEach(s => {
    const name = s.dataset.func;
    const pname = s.dataset.param;
    if (functionsData[name] && functionsData[name].params[pname]) {
      const cfg = SLIDER_CONFIG[name] || {min:0,max:1,step:0.05};
      s.value = functionsData[name].params[pname].default ?? cfg.min;
      const step = parseFloat(s.step);
      s.nextElementSibling.textContent = step < 0.1 ? parseFloat(s.value).toFixed(2) : parseFloat(s.value).toFixed(step < 1 ? 1 : 0);
    }
  });
  scheduleRender();
}

document.getElementById('fileInput').addEventListener('change', e => {
  currentFile = e.target.files[0];
  if (!currentFile) return;
  document.getElementById('placeholder').style.display = 'none';
  const origImg = document.getElementById('originalImg');
  const url = URL.createObjectURL(currentFile);
  origImg.onload = () => URL.revokeObjectURL(url);
  origImg.src = url;
  origImg.style.display = 'block';
  document.getElementById('status').textContent = currentFile.name;
  scheduleRender();
});

init();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    load_generate_module()
    print("Filter Lab running at http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
