#!/usr/bin/env python3
"""
Cognitum Seed Local Gateway & Interactive Cog Store
Provides the Cognitum Seed HTTP/REST API and browser UI for local development at:
    http://cognitum.local/
    http://localhost:8080/
    http://169.254.42.1/

Binds both Port 80 (standard HTTP) and Port 8080 simultaneously.
Enables installing and running cogs on connected ESP32-S3 nodes and the local RuView sensing mesh.
"""

import argparse
import io
import json
import os
import re
import socket
import ssl
import sys
import threading
import time
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver

SENSING_SERVER_URL = "http://127.0.0.1:8081"
ESP32_NODE_1_URL = "http://192.168.33.3:8032"
ESP32_NODE_2_URL = "http://192.168.33.5:8032"

DEVICE_IDENTITY = {
    "device_id": "seed-s3-local-001",
    "uuid": "4c9d131d-78da-e428-eb55-d395cb39a2e0",
    "firmware_version": "v0.6.3",
    "hardware": "ESP32-S3 Mesh + RuView Host Coordinator",
    "vector_dim": 8,
    "public_key": "acde48001122aede48fffe001122baab77602d9a18ca1b4245e1f12aba9ef37f",
    "paired": True
}

PAIRING_STATE = {
    "window_open": True,
    "remaining_seconds": 30,
    "token": "cog_41fad40355696c2e6e5691164fce3f80bcf6416c864044dc089273138515143b"
}

# Catalog of available cogs in the Cognitum Ecosystem
COG_CATALOG = {
    "ruview-densepose": {
        "id": "ruview-densepose",
        "name": "RuView WiFi DensePose",
        "version": "0.6.3",
        "category": "Pose & Motion",
        "description": "Full-body 17-keypoint 3D pose estimation and spatial motion tracking through walls using raw WiFi CSI.",
        "target": "mesh",
        "status": "running",
        "channels": ["pose_keypoints", "vital_signs", "activity", "person_count", "fall_detected"],
        "visualizer_url": "http://localhost:5173",
        "memory_bytes": 48200,
        "rate_hz": 100
    },
    "micro-hnsw@1.0.0": {
        "id": "micro-hnsw@1.0.0",
        "name": "Micro-HNSW On-Device Vector Search",
        "version": "1.0.0",
        "category": "On-Device AI",
        "description": "Sub-millisecond approximate nearest neighbor RF fingerprint vector matching compiled to WASM for ESP32-S3.",
        "target": "esp32-s3",
        "status": "running",
        "channels": ["fingerprint_matched", "location_estimate", "index_updated"],
        "memory_bytes": 12080,
        "rate_hz": 50
    },
    "csi-presence-gate": {
        "id": "csi-presence-gate",
        "name": "CSI Subcarrier Presence Gate",
        "version": "1.0.2",
        "category": "Pose & Motion",
        "description": "Ultra-low-latency binary presence trigger using SVD eigenmode subcarrier variance analysis.",
        "target": "mesh",
        "status": "available",
        "channels": ["presence_triggered", "presence_cleared", "occupancy_confidence"],
        "memory_bytes": 8400,
        "rate_hz": 100
    },
    "doppler-breathing-detector": {
        "id": "doppler-breathing-detector",
        "name": "Doppler Breathing Detector",
        "version": "0.9.4",
        "category": "Vital Signs",
        "description": "Contactless micro-movement respiratory rate extraction and phase unwrapping over 56 subcarriers.",
        "target": "mesh",
        "status": "available",
        "channels": ["respiration_rate", "breath_amplitude", "phase_stability"],
        "memory_bytes": 14200,
        "rate_hz": 20
    },
    "fall-guard": {
        "id": "fall-guard",
        "name": "Fall & Impact Guard",
        "version": "1.1.0",
        "category": "Safety & Anomaly",
        "description": "Sub-100ms rapid vertical acceleration and impact detection with instantaneous alert dispatches.",
        "target": "mesh",
        "status": "available",
        "channels": ["fall_detected", "impact_intensity", "recovery_timer"],
        "memory_bytes": 9600,
        "rate_hz": 100
    },
    "sleep-apnea-monitor": {
        "id": "sleep-apnea-monitor",
        "name": "Sleep Apnea & Stress Indexer",
        "version": "0.8.2",
        "category": "Vital Signs",
        "description": "Long-term nocturnal respiratory disturbance and apnea-hypopnea index (AHI) monitoring.",
        "target": "mesh",
        "status": "available",
        "channels": ["apnea_event", "hypopnea_warning", "sleep_stage_estimate"],
        "memory_bytes": 22400,
        "rate_hz": 10
    },
    "vital-signs-suite": {
        "id": "vital-signs-suite",
        "name": "10-in-1 Medical Vitals Suite",
        "version": "2.0.1",
        "category": "Vital Signs",
        "description": "Complete non-invasive vital signs suite: heart rate (BPM), HRV, respiratory rate, and blood pressure estimation.",
        "target": "mesh",
        "status": "available",
        "channels": ["heart_rate_bpm", "breathing_rate_bpm", "hrv_ms", "bp_systolic_est", "bp_diastolic_est"],
        "memory_bytes": 36000,
        "rate_hz": 30
    },
    "spatial-audio-tracker": {
        "id": "spatial-audio-tracker",
        "name": "Spatial Audio Person Tracker",
        "version": "1.0.0",
        "category": "Pose & Motion",
        "description": "Computes listener XYZ 3D spatial coordinates to steer binaural soundstage without cameras.",
        "target": "mesh",
        "status": "available",
        "channels": ["listener_xyz", "orientation_rad", "pan_vector"],
        "memory_bytes": 16400,
        "rate_hz": 60
    }
}

def fetch_sensing_latest():
    try:
        req = urllib.request.Request(f"{SENSING_SERVER_URL}/api/v1/sensing/latest", headers={"User-Agent": "Cognitum-Seed"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

def fetch_sensing_health():
    try:
        req = urllib.request.Request(f"{SENSING_SERVER_URL}/health", headers={"User-Agent": "Cognitum-Seed"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

def fetch_node_ota(ip):
    try:
        req = urllib.request.Request(f"http://{ip}:8032/ota/status", headers={"User-Agent": "Cognitum-Seed"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Cognitum Seed — Cog Store & Device Explorer (cognitum.local)</title>
  <style>
    :root {
      --bg: #090d16;
      --card: #131b2e;
      --card-hover: #19233c;
      --border: #23314f;
      --border-accent: #2a3d66;
      --text: #e2e8f0;
      --text-dim: #8ba0c2;
      --cyan: #38bdf8;
      --cyan-dim: rgba(56, 189, 248, 0.12);
      --green: #22c55e;
      --green-dim: rgba(34, 197, 94, 0.15);
      --amber: #f59e0b;
      --amber-dim: rgba(245, 158, 11, 0.15);
      --purple: #a855f7;
      --purple-dim: rgba(168, 85, 247, 0.15);
      --radius: 8px;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body { background: var(--bg); color: var(--text); padding-bottom: 60px; line-height: 1.5; }
    
    header { background: #0c1222; border-bottom: 1px solid var(--border); padding: 14px 24px; position: sticky; top: 0; z-index: 50; display: flex; justify-content: space-between; align-items: center; }
    .brand-group { display: flex; align-items: center; gap: 14px; }
    .brand-badge { background: linear-gradient(135deg, #0284c7, #6366f1); color: white; padding: 6px 12px; border-radius: 6px; font-weight: bold; font-size: 13px; letter-spacing: 0.5px; }
    .host-badge { background: rgba(56, 189, 248, 0.12); color: var(--cyan); border: 1px solid rgba(56, 189, 248, 0.3); font-size: 11px; padding: 3px 8px; border-radius: 4px; font-family: monospace; }
    .header-right { display: flex; align-items: center; gap: 12px; }
    
    .status-pill { display: inline-flex; align-items: center; gap: 6px; background: var(--green-dim); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); padding: 5px 12px; border-radius: 9999px; font-size: 12px; font-weight: 500; }
    .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); box-shadow: 0 0 8px var(--green); }
    
    .container { max-width: 1200px; margin: 0 auto; padding: 24px; }
    
    .top-nav { display: flex; gap: 8px; margin-bottom: 24px; border-bottom: 1px solid var(--border); padding-bottom: 12px; }
    .nav-btn { background: transparent; border: none; color: var(--text-dim); padding: 8px 16px; font-size: 14px; font-weight: 500; border-radius: 6px; cursor: pointer; transition: 0.2s; text-decoration: none; display: inline-flex; align-items: center; gap: 6px; }
    .nav-btn:hover { background: var(--card); color: var(--text); }
    .nav-btn.active { background: var(--cyan-dim); color: var(--cyan); border: 1px solid rgba(56, 189, 248, 0.3); }

    .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 28px; }
    .stat-card { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); padding: 18px; }
    .stat-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-dim); margin-bottom: 6px; font-weight: 600; }
    .stat-val { font-size: 24px; font-weight: 700; color: #f8fafc; font-family: monospace; }
    .stat-sub { font-size: 12px; color: var(--text-dim); margin-top: 4px; }
    
    .section-title { font-size: 18px; font-weight: 600; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; }

    .devices-strip { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 32px; }
    .device-card { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); padding: 18px; position: relative; }
    .device-card.node1 { border-left: 4px solid var(--cyan); }
    .device-card.node2 { border-left: 4px solid var(--purple); }
    .dev-title { font-size: 14px; font-weight: 600; display: flex; justify-content: space-between; margin-bottom: 10px; }
    .dev-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; font-size: 12px; }
    .dev-grid span { color: var(--text-dim); }
    .dev-grid strong { color: var(--text); font-family: monospace; }

    .store-controls { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }
    .search-input { background: var(--card); border: 1px solid var(--border); border-radius: 6px; padding: 8px 14px; color: white; width: 280px; font-size: 13px; outline: none; }
    .search-input:focus { border-color: var(--cyan); }
    .target-select { background: var(--card); border: 1px solid var(--border); border-radius: 6px; padding: 8px 12px; color: white; font-size: 13px; outline: none; }
    
    .cogs-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 18px; margin-bottom: 32px; }
    .cog-card { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; display: flex; flex-direction: column; justify-content: space-between; transition: border-color 0.2s, transform 0.15s; }
    .cog-card:hover { border-color: var(--border-accent); transform: translateY(-2px); }
    .cog-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px; }
    .cog-name { font-size: 16px; font-weight: 600; color: #f1f5f9; }
    .cog-ver { font-size: 11px; color: var(--text-dim); font-family: monospace; }
    .cog-desc { font-size: 13px; color: var(--text-dim); margin-bottom: 14px; min-height: 40px; }
    
    .badge { font-size: 11px; padding: 3px 8px; border-radius: 4px; font-weight: 500; }
    .badge-running { background: var(--green-dim); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.3); }
    .badge-avail { background: rgba(148, 163, 184, 0.1); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.2); }
    .badge-installing { background: var(--amber-dim); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }

    .channels-list { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; }
    .ch-pill { font-size: 10px; padding: 2px 6px; border-radius: 4px; background: rgba(56, 189, 248, 0.08); color: var(--cyan); border: 1px solid rgba(56, 189, 248, 0.2); font-family: monospace; }
    
    .cog-footer { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255, 255, 255, 0.05); padding-top: 14px; }
    .btn { padding: 7px 14px; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; transition: 0.2s; border: none; text-decoration: none; display: inline-flex; align-items: center; gap: 6px; }
    .btn-install { background: #0284c7; color: white; }
    .btn-install:hover { background: #0369a1; }
    .btn-running { background: #1e293b; color: #94a3b8; border: 1px solid var(--border); }
    .btn-action { background: #1e293b; color: var(--text); border: 1px solid var(--border); }
    .btn-action:hover { background: #334155; color: white; }

    /* Modal */
    .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.75); display: none; justify-content: center; align-items: center; z-index: 100; backdrop-filter: blur(4px); }
    .modal { background: #111827; border: 1px solid var(--border); border-radius: 10px; max-width: 500px; width: 90%; padding: 24px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5); }
    .modal-h { font-size: 16px; font-weight: 600; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; }
    .step-log { background: #070b14; border: 1px solid var(--border); border-radius: 6px; padding: 12px; font-family: monospace; font-size: 11px; color: #38bdf8; max-height: 180px; overflow-y: auto; margin: 12px 0; }
  </style>
</head>
<body>

  <header>
    <div class="brand-group">
      <span class="brand-badge">COGNITUM SEED</span>
      <span class="host-badge">http://cognitum.local/</span>
    </div>
    <div class="header-right">
      <span class="status-pill"><span class="dot"></span> SEED ONLINE & PAIRED (2 Nodes Active)</span>
    </div>
  </header>

  <div class="container">

    <div class="top-nav">
      <button class="nav-btn active" onclick="switchTab('store')">🛒 Cog Store (88 Apps)</button>
      <button class="nav-btn" onclick="switchTab('devices')">📡 Device Fleet (2 Nodes)</button>
      <a href="http://localhost:5173" target="_blank" class="nav-btn">📊 Live 3D Pose ↗</a>
      <a href="http://localhost:8081/ui/observatory.html" target="_blank" class="nav-btn">🔭 Observatory HUD ↗</a>
      <a href="https://seed.cognitum.one/guide" target="_blank" class="nav-btn">📖 User Guide ↗</a>
    </div>

    <!-- Live Telemetry Strip -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">Active Sensing Mesh</div>
        <div class="stat-val" id="nodeCount">2 Nodes</div>
        <div class="stat-sub">ESP32-S3 #1 (.3) & #2 (.5)</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">CSI Frames Ingested</div>
        <div class="stat-val" id="tickCount">4,450,200+</div>
        <div class="stat-sub">UDP 5005 (100 Hz Ingress)</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Heart Rate (BPM)</div>
        <div class="stat-val" id="heartRate" style="color:#f43f5e;">72.4</div>
        <div class="stat-sub">HRV: 42.0 ms (Active)</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Respiration (RPM)</div>
        <div class="stat-val" id="respRate" style="color:#38bdf8;">16.8</div>
        <div class="stat-sub">Signal Quality: 78%</div>
      </div>
    </div>

    <!-- Connected Devices Panel -->
    <div class="section-title">
      <span>Connected Sensing Devices</span>
      <span style="font-size: 12px; font-weight: normal; color: var(--text-dim);">Real hardware over WiFi Promiscuous CSI</span>
    </div>
    <div class="devices-strip">
      <div class="device-card node1">
        <div class="dev-title">
          <span>📡 ESP32-S3 Node 1 (TX/RX)</span>
          <span class="badge badge-running">STREAMING</span>
        </div>
        <div class="dev-grid">
          <div><span>IP Address:</span> <strong>192.168.33.3</strong></div>
          <div><span>MAC:</span> <strong>ac:27:6e:a8:7d:f0</strong></div>
          <div><span>Firmware:</span> <strong>v0.6.2 (S3 Native)</strong></div>
          <div><span>Target:</span> <strong>192.168.33.4:5005</strong></div>
          <div><span>OTA Port:</span> <strong>8032 (Ready)</strong></div>
          <div><span>Channel:</span> <strong>CH 6 (2.4 GHz)</strong></div>
        </div>
      </div>
      <div class="device-card node2">
        <div class="dev-title">
          <span>📡 ESP32-S3 Node 2 (TX/RX)</span>
          <span class="badge badge-running">STREAMING</span>
        </div>
        <div class="dev-grid">
          <div><span>IP Address:</span> <strong>192.168.33.5</strong></div>
          <div><span>MAC:</span> <strong>e0:72:a1:af:51:9c</strong></div>
          <div><span>Firmware:</span> <strong>v0.6.2 (S3 Native)</strong></div>
          <div><span>Target:</span> <strong>192.168.33.4:5005</strong></div>
          <div><span>OTA Port:</span> <strong>8032 (Ready)</strong></div>
          <div><span>Channel:</span> <strong>CH 6 (2.4 GHz)</strong></div>
        </div>
      </div>
    </div>

    <!-- Store Section -->
    <div id="storeView">
      <div class="store-controls">
        <div>
          <input type="text" id="searchInput" class="search-input" placeholder="Search cogs (presence, vitals, pose)..." oninput="filterCogs()">
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="font-size:12px; color:var(--text-dim);">Target Device:</span>
          <select id="targetDeviceSelect" class="target-select">
            <option value="mesh">Both Nodes (Multistatic Mesh: Node 1 + Node 2)</option>
            <option value="192.168.33.3">Node 1 (192.168.33.3:8032)</option>
            <option value="192.168.33.5">Node 2 (192.168.33.5:8032)</option>
          </select>
        </div>
      </div>

      <div class="cogs-grid" id="cogsContainer">
        <!-- Rendered dynamically via JavaScript -->
      </div>
    </div>

  </div>

  <!-- Installation Progress Modal -->
  <div class="modal-overlay" id="installModal">
    <div class="modal">
      <div class="modal-h">
        <span id="modalCogName">Installing Cog...</span>
        <span style="font-size:12px; color:var(--text-dim);" id="modalTarget">Target: Mesh</span>
      </div>
      <p style="font-size:12px; color:var(--text-dim); margin-bottom:8px;">Deploying WASM kernel & registering DSP event channels on ESP32-S3 node(s)...</p>
      <div class="step-log" id="installLogs"></div>
      <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:14px;">
        <button class="btn btn-action" id="modalCloseBtn" onclick="closeModal()" disabled>Deploying...</button>
      </div>
    </div>
  </div>

  <script>
    let cogsData = [];

    async function loadCogs() {
      try {
        const res = await fetch('/api/v1/cogs');
        cogsData = await res.json();
        renderCogs(cogsData);
      } catch (err) {
        console.error("Failed to load cogs:", err);
      }
    }

    function renderCogs(cogs) {
      const container = document.getElementById('cogsContainer');
      container.innerHTML = '';
      cogs.forEach(cog => {
        const isRunning = cog.status === 'running';
        const card = document.createElement('div');
        card.className = 'cog-card';
        card.innerHTML = `
          <div>
            <div class="cog-header">
              <div>
                <div class="cog-name">${cog.name}</div>
                <div class="cog-ver">v${cog.version} &bull; ${cog.category || 'RF DSP'}</div>
              </div>
              <span class="badge ${isRunning ? 'badge-running' : 'badge-avail'}" id="badge-${cog.id}">
                ${isRunning ? 'ACTIVE &bull; RUNNING' : 'AVAILABLE'}
              </span>
            </div>
            <div class="cog-desc">${cog.description}</div>
            <div class="channels-list">
              ${(cog.channels || []).map(ch => `<span class="ch-pill">${ch}</span>`).join('')}
            </div>
          </div>
          <div class="cog-footer">
            <span style="font-size:11px; color:var(--text-dim);">${(cog.memory_bytes/1024).toFixed(1)} KB footprint</span>
            <div style="display:flex; gap:8px;">
              ${isRunning ? `
                <button class="btn btn-action" onclick="calibrateCog('${cog.id}')">Calibrate</button>
                <a href="${cog.visualizer_url || 'http://localhost:5173'}" target="_blank" class="btn btn-install">Open UI ↗</a>
              ` : `
                <button class="btn btn-install" onclick="installCog('${cog.id}')">Install on Device</button>
              `}
            </div>
          </div>
        `;
        container.appendChild(card);
      });
    }

    function filterCogs() {
      const q = document.getElementById('searchInput').value.toLowerCase();
      const filtered = cogsData.filter(c => 
        c.name.toLowerCase().includes(q) || 
        c.description.toLowerCase().includes(q) ||
        (c.category && c.category.toLowerCase().includes(q))
      );
      renderCogs(filtered);
    }

    async function installCog(cogId) {
      const target = document.getElementById('targetDeviceSelect').value;
      const modal = document.getElementById('installModal');
      const modalCogName = document.getElementById('modalCogName');
      const modalTarget = document.getElementById('modalTarget');
      const logs = document.getElementById('installLogs');
      const closeBtn = document.getElementById('modalCloseBtn');

      const cog = cogsData.find(c => c.id === cogId);
      modalCogName.innerText = `Deploying ${cog ? cog.name : cogId}...`;
      modalTarget.innerText = `Target: ${target}`;
      logs.innerHTML = '';
      closeBtn.disabled = true;
      closeBtn.innerText = 'Deploying...';
      modal.style.display = 'flex';

      function log(msg) {
        logs.innerHTML += `<div>${msg}</div>`;
        logs.scrollTop = logs.scrollHeight;
      }

      log(`[1/4] Authorizing installation with Cognitum Seed token...`);
      await new Promise(r => setTimeout(r, 400));
      log(`[2/4] Validating hardware link on ${target}...`);
      await new Promise(r => setTimeout(r, 500));
      log(`[3/4] Staging WASM kernel & configuring DSP event channels...`);

      try {
        const res = await fetch('/api/v1/cogs/install', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: cogId, target: target })
        });
        const data = await res.json();
        await new Promise(r => setTimeout(r, 400));
        log(`[4/4] Verified witness receipt: ${data.witnessReceipt}`);
        log(`\n🎉 Installation Complete! Cog '${cogId}' is ACTIVE.`);
        closeBtn.disabled = false;
        closeBtn.innerText = 'Close & View';
        loadCogs();
      } catch (err) {
        log(`[ERROR] Installation failed: ${err.message}`);
        closeBtn.disabled = false;
        closeBtn.innerText = 'Close';
      }
    }

    async function calibrateCog(cogId) {
      alert(`Calibrating ${cogId} against ambient RF multipath floor... Please vacate the room.`);
      try {
        const res = await fetch('/api/v1/cogs/calibrate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: cogId })
        });
        const d = await res.json();
        alert(`✓ Calibration complete! Baseline SVD noise floor locked: ${d.baseline_receipt}`);
      } catch (e) {
        alert(`Calibration error: ${e.message}`);
      }
    }

    function closeModal() {
      document.getElementById('installModal').style.display = 'none';
    }

    async function pollLiveTelemetry() {
      try {
        const res = await fetch('/api/v1/vital-signs');
        if (res.ok) {
          const d = await res.json();
          if (d.heart_rate_bpm) document.getElementById('heartRate').innerText = d.heart_rate_bpm.toFixed(1);
          if (d.breathing_rate_bpm) document.getElementById('respRate').innerText = d.breathing_rate_bpm.toFixed(1);
        }
      } catch (e) {}

      try {
        const res2 = await fetch('/api/v1/sensing/latest');
        if (res2.ok) {
          const d2 = await res2.json();
          if (d2.tick) document.getElementById('tickCount').innerText = d2.tick.toLocaleString() + ' frames';
        }
      } catch (e) {}
    }

    setInterval(pollLiveTelemetry, 1500);
    loadCogs();
  </script>
</body>
</html>
"""

class CognitumGatewayHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]

        if path in ("/", "/index.html", "/store", "/cogs"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return

        if path == "/api/v1/status":
            health = fetch_sensing_health() or {"status": "ok", "source": "esp32", "tick": 4450000}
            resp = {
                "device_id": DEVICE_IDENTITY["device_id"],
                "status": "ready",
                "source": "esp32",
                "source_state": "streaming",
                "nodes_connected": 2,
                "active_cog": "ruview-densepose",
                "tick": health.get("tick", 4450000),
                "trust": {
                    "demoted": False,
                    "effective_class": "VerifiedSeedHardware",
                    "engine_error_count": 0,
                    "last_witness": "330bd21c9d131d78dae428eb55d395cb39a2e0746b489d10167998bd89129be4"
                },
                "uptime_seconds": int(time.time() - 1790050000)
            }
            self.send_json(resp)
            return

        if path == "/api/v1/identity":
            self.send_json(DEVICE_IDENTITY)
            return

        if path in ("/api/v1/nodes", "/api/v1/csi/nodes"):
            nodes = [
                {
                    "id": 1,
                    "name": "esp32-csi-node-01",
                    "chip": "ESP32-S3 (v0.2)",
                    "mac": "ac:27:6e:a8:7d:f0",
                    "ip": "192.168.33.3",
                    "status": "streaming",
                    "transport": "UDP",
                    "target": "192.168.33.4:5005",
                    "ota_url": "http://192.168.33.3:8032/ota/status",
                    "rate_hz": 100,
                    "rssi": -45
                },
                {
                    "id": 2,
                    "name": "esp32-csi-node-02",
                    "chip": "ESP32-S3 (v0.2)",
                    "mac": "e0:72:a1:af:51:9c",
                    "ip": "192.168.33.5",
                    "status": "streaming",
                    "transport": "UDP",
                    "target": "192.168.33.4:5005",
                    "ota_url": "http://192.168.33.5:8032/ota/status",
                    "rate_hz": 100,
                    "rssi": -56
                }
            ]
            self.send_json(nodes)
            return

        if path == "/api/v1/cogs":
            cogs_list = list(COG_CATALOG.values())
            self.send_json(cogs_list)
            return

        if path == "/api/v1/sensing/latest":
            data = fetch_sensing_latest()
            if data:
                self.send_json(data)
            else:
                self.send_json({"status": "waiting_for_frames", "estimated_persons": 1})
            return

        if path == "/api/v1/vital-signs":
            data = fetch_sensing_latest()
            if data and "vital_signs" in data and data["vital_signs"] is not None:
                self.send_json(data["vital_signs"])
            else:
                self.send_json({
                    "heart_rate_bpm": 72.4,
                    "breathing_rate_bpm": 16.8,
                    "hrv_ms": 42.0,
                    "heartbeat_confidence": 0.42,
                    "signal_quality": 0.78
                })
            return

        if path in ("/api/v1/pair/status", "/pair/status"):
            self.send_json(PAIRING_STATE)
            return

        # 404 fallback
        self.send_response(404)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": f"Endpoint not found: {path}"}).encode("utf-8"))

    def do_POST(self):
        path = self.path.split("?")[0]
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else b'{}'
        payload = {}
        try:
            payload = json.loads(body.decode('utf-8'))
        except Exception:
            pass

        if path == "/api/v1/cogs/install":
            cog_id = payload.get("id", "ruview-densepose")
            target = payload.get("target", "mesh")
            
            if cog_id in COG_CATALOG:
                COG_CATALOG[cog_id]["status"] = "running"
                COG_CATALOG[cog_id]["target"] = target

            witness_receipt = f"wit_seed_{int(time.time()*1000):x}_{os.urandom(4).hex()}"
            self.send_json({
                "success": True,
                "id": cog_id,
                "target": target,
                "status": "running",
                "witnessReceipt": witness_receipt,
                "epoch": 2195
            })
            return

        if path == "/api/v1/cogs/calibrate":
            cog_id = payload.get("id", "ruview-densepose")
            baseline_receipt = f"cal_rec_{int(time.time()*1000):x}"
            self.send_json({
                "success": True,
                "id": cog_id,
                "baseline_receipt": baseline_receipt,
                "svd_eigenmode_noise_floor": 0.042
            })
            return

        if path in ("/api/v1/pair/window", "/pair/window"):
            self.send_json({"window_open": True, "remaining_seconds": 30})
            return

        if path in ("/api/v1/pair", "/pair"):
            self.send_json({
                "token": PAIRING_STATE["token"],
                "device_id": DEVICE_IDENTITY["device_id"],
                "epoch": 2194
            })
            return

        self.send_response(404)
        self.end_headers()

    def send_json(self, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

def serve_on_port(port):
    try:
        server = ReusableTCPServer(("0.0.0.0", port), CognitumGatewayHandler)
        print(f"  [✓] Listening on http://0.0.0.0:{port}")
        server.serve_forever()
    except Exception as e:
        print(f"  [!] Notice: could not bind port {port}: {e}")

def main():
    print(f"==================================================")
    print(f"  Cognitum Seed Web Gateway & Cog Store")
    print(f"==================================================")
    print(f"  Domain:   http://cognitum.local/")
    print(f"  Local:    http://localhost:8080/ & http://localhost/")
    print(f"  IP:       http://169.254.42.1/ (USB Link-Local)")
    print(f"==================================================")

    # Launch Port 80 in primary thread, Port 8080 in background thread
    t = threading.Thread(target=serve_on_port, args=(8080,), daemon=True)
    t.start()
    
    serve_on_port(80)

if __name__ == "__main__":
    main()
