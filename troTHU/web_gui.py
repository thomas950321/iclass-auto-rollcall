import asyncio
import socket
import webbrowser
import types
import contextvars
import uuid
import time
import copy
from aiohttp import web
import troTHU.runtime_context as ctx


# Global task tracker
monitor_task = None
shutdown_event = None

HTML_CONTENT = """<!doctype html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <meta name="theme-color" content="#0b1020"/>
  <title>iClass 自動簽到助手</title>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
  <link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Noto+Sans+TC:wght@400;500;600;700;800&display=swap" rel="stylesheet"/>
  <style>
    /* ── Design Tokens ── */
    :root {
      --bg:       #0b1020;
      --surface:  #111928;
      --surface2: #161f30;
      --line:     rgba(255,255,255,.07);
      --violet:   #6768ff;
      --violet-d: #938bff;
      --mint:     #27d39b;
      --amber:    #f5b94d;
      --red:      #ff687c;
      --text:     #d7dcef;
      --muted:    #7e8ba7;
      --subtle:   #4a5570;
      --shadow:   0 8px 32px rgba(0,0,0,.45);
    }

    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    html, body {
      max-width: 100vw;
      overflow-x: hidden;
    }

    body {
      font-family: 'Noto Sans TC', sans-serif;
      background: var(--bg);
      color: var(--text);
      font-size: 13px;
      min-height: 100vh;
      -webkit-tap-highlight-color: transparent;
    }

    button { font-family: inherit; cursor: pointer; border: none; background: none; color: inherit; }
    input, select { font-family: inherit; }
    strong { font-weight: 600; }

    /* ── App Shell ── */
    .app-shell {
      display: flex;
      min-height: 100vh;
      width: 100%;
      max-width: 100vw;
      overflow-x: hidden;
    }

    /* ── Sidebar ── */
    .sidebar {
      width: 240px;
      flex-shrink: 0;
      background: var(--surface);
      border-right: 1px solid var(--line);
      display: flex;
      flex-direction: column;
      padding: 24px 16px;
      position: fixed;
      top: 0; left: 0; bottom: 0;
      z-index: 10;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 0 8px 24px;
      border-bottom: 1px solid var(--line);
      margin-bottom: 20px;
    }

    .brand-mark {
      display: flex;
      flex-direction: column;
      gap: 3px;
    }

    .brand-mark span {
      display: block;
      height: 4px;
      border-radius: 2px;
      background: var(--violet);
    }
    .brand-mark span:nth-child(1) { width: 20px; }
    .brand-mark span:nth-child(2) { width: 14px; opacity: .6; }
    .brand-mark span:nth-child(3) { width: 9px;  opacity: .3; }

    .brand strong { font-size: 15px; font-weight: 700; display: block; }
    .brand small  { font-size: 10px; color: var(--muted); display: block; margin-top: 1px; }

    .sidebar-label {
      font-size: 9px;
      font-weight: 700;
      letter-spacing: 1.2px;
      text-transform: uppercase;
      color: var(--subtle);
      padding: 0 8px;
      margin-bottom: 6px;
    }

    .side-nav { display: flex; flex-direction: column; gap: 2px; }

    .nav-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 12px;
      border-radius: 10px;
      font-size: 13px;
      color: var(--muted);
      transition: background .15s, color .15s;
      width: 100%;
      text-align: left;
    }

    .nav-item:hover { background: rgba(255,255,255,.04); color: var(--text); }
    .nav-item.active { background: rgba(103,104,255,.13); color: var(--violet-d); }

    .nav-icon { font-size: 16px; width: 20px; text-align: center; }

    .nav-item b {
      margin-left: auto;
      font-size: 9px;
      font-weight: 700;
      background: var(--violet);
      color: #fff;
      border-radius: 20px;
      padding: 1px 6px;
    }

    .sidebar-bottom { margin-top: auto; }

    .mini-account {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 12px 8px;
      border-top: 1px solid var(--line);
      margin-bottom: 10px;
    }

    .avatar {
      width: 34px; height: 34px;
      background: linear-gradient(135deg, var(--violet), #9c6bff);
      border-radius: 10px;
      font-size: 11px;
      font-weight: 700;
      display: grid;
      place-items: center;
      flex-shrink: 0;
    }

    .mini-account > div { overflow: hidden; }
    .mini-account strong { font-size: 11px; display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .mini-account span { font-size: 9px; color: var(--muted); display: block; font-family: 'DM Mono', monospace; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

    .online-dot {
      width: 7px; height: 7px;
      background: var(--mint);
      border-radius: 50%;
      flex-shrink: 0;
      margin-left: auto;
    }

    .sidebar-note {
      font-size: 9px;
      color: var(--subtle);
      padding: 0 8px;
      display: flex;
      align-items: center;
      gap: 5px;
    }

    .pulse-dot {
      width: 5px; height: 5px;
      background: var(--mint);
      border-radius: 50%;
      display: inline-block;
      animation: pulse 2s infinite;
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50%       { opacity: .3; }
    }

    /* ── Main Content ── */
    .main-content {
      margin-left: 240px;
      flex: 1;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      min-width: 0;
      max-width: 100%;
      overflow-x: hidden;
    }

    .topbar {
      height: 56px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      padding: 0 28px;
      position: sticky;
      top: 0;
      background: rgba(11,16,32,.85);
      backdrop-filter: blur(12px);
      z-index: 5;
    }

    .breadcrumb {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      color: var(--muted);
    }

    .breadcrumb strong { color: var(--text); font-weight: 600; }
    .breadcrumb .slash { color: var(--subtle); }

    .top-actions {
      margin-left: auto;
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .demo-badge {
      font-size: 9px;
      font-weight: 700;
      letter-spacing: 1px;
      background: rgba(103,104,255,.15);
      color: var(--violet-d);
      border: 1px solid rgba(103,104,255,.25);
      border-radius: 4px;
      padding: 3px 7px;
    }

    .icon-button {
      width: 32px; height: 32px;
      border-radius: 8px;
      display: grid;
      place-items: center;
      font-size: 16px;
      color: var(--muted);
      transition: background .15s, color .15s;
    }

    .icon-button:hover { background: rgba(255,255,255,.05); color: var(--text); }

    .mobile-brand { display: none; }
    .mobile-menu  { display: none; }

    /* ── Views ── */
    .view { display: none; padding: 32px 28px 48px; min-width: 0; max-width: 100%; box-sizing: border-box; }
    .view.active { display: block; }

    /* ── Page Heading ── */
    .page-heading {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      margin-bottom: 28px;
    }

    .page-heading.compact { align-items: center; margin-bottom: 22px; }

    .eyebrow {
      font-size: 11px;
      color: var(--muted);
      letter-spacing: .5px;
      margin-bottom: 5px;
    }

    .page-heading h1 {
      font-size: 30px;
      font-weight: 800;
      letter-spacing: -.5px;
      line-height: 1.1;
    }

    .heading-copy {
      font-size: 12px;
      color: var(--muted);
      margin-top: 8px;
      line-height: 1.6;
    }

    .heading-time {
      text-align: right;
    }

    .heading-time span { font-size: 10px; color: var(--subtle); display: block; margin-bottom: 2px; }
    .heading-time strong { font-size: 26px; font-weight: 700; font-family: 'DM Mono', monospace; }

    /* ── Monitor Card ── */
    .monitor-card {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 22px 24px 20px;
      margin-bottom: 20px;
      position: relative;
      overflow: hidden;
    }

    .monitor-glow {
      position: absolute;
      top: -40px; right: -40px;
      width: 160px; height: 160px;
      background: radial-gradient(circle, rgba(103,104,255,.18), transparent 70%);
      pointer-events: none;
    }

    .monitor-topline {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 18px;
    }

    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 10px;
      font-weight: 600;
      padding: 5px 11px;
      border-radius: 20px;
      background: rgba(39,211,155,.1);
      color: var(--mint);
      border: 1px solid rgba(39,211,155,.2);
    }

    .status-pill.off {
      background: rgba(255,104,124,.08);
      color: var(--red);
      border-color: rgba(255,104,124,.2);
    }

    .status-pill > span:first-child {
      width: 6px; height: 6px;
      border-radius: 50%;
      background: currentColor;
    }

    .more-button { color: var(--subtle); font-size: 14px; letter-spacing: 1px; }

    .monitor-main {
      display: flex;
      align-items: center;
      justify-content: space-between;
      min-height: 100px;
      padding: 10px 0 14px;
    }

    .card-kicker {
      font-size: 9px;
      text-transform: uppercase;
      letter-spacing: 1px;
      color: var(--subtle);
      display: block;
      margin-bottom: 8px;
    }

    .monitor-main h2 {
      font-size: 20px;
      font-weight: 700;
      line-height: 1.3;
      max-width: 240px;
    }

    .monitor-main p {
      font-size: 11px;
      color: var(--muted);
      margin-top: 7px;
      line-height: 1.6;
      max-width: 230px;
    }

    /* Radar orb */
    .radar-orb {
      width: 90px; height: 90px;
      position: relative;
      flex-shrink: 0;
    }

    .orb-ring {
      position: absolute;
      border-radius: 50%;
      border: 1px solid rgba(103,104,255,.3);
      animation: orb-spin linear infinite;
    }

    .ring-one {
      inset: 0;
      animation-duration: 4s;
    }

    .ring-two {
      inset: 12px;
      border-color: rgba(103,104,255,.15);
      animation-duration: 7s;
      animation-direction: reverse;
    }

    @keyframes orb-spin {
      to { transform: rotate(360deg); }
    }

    .orb-core {
      position: absolute;
      inset: 28px;
      background: rgba(103,104,255,.12);
      border-radius: 50%;
      display: grid;
      place-items: center;
    }

    .orb-core span {
      width: 10px; height: 10px;
      background: var(--violet);
      border-radius: 50%;
      box-shadow: 0 0 12px var(--violet);
    }

    .monitor-bottom {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-top: 16px;
      border-top: 1px solid var(--line);
      gap: 16px;
    }

    .status-metrics {
      display: flex;
      gap: 24px;
    }

    .status-metrics > div span { font-size: 9px; color: var(--subtle); display: block; margin-bottom: 3px; }
    .status-metrics > div strong { font-size: 12px; font-weight: 600; }

    .mode-text { color: var(--violet-d); }

    /* Timer row & options */
    .timer-row {
      display: flex;
      align-items: center;
      gap: 10px;
      padding-top: 14px;
      border-top: 1px solid var(--line);
      margin-top: 14px;
      flex-wrap: wrap;
    }

    .timer-label {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      font-weight: 500;
      color: var(--muted);
      white-space: nowrap;
    }

    .timer-options {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }

    .timer-opt {
      font-size: 11px;
      font-weight: 500;
      color: var(--muted);
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid var(--line);
      border-radius: 7px;
      padding: 4px 11px;
      transition: all .15s ease;
      cursor: pointer;
      user-select: none;
    }

    .timer-opt:hover:not(:disabled) {
      color: var(--text);
      background: rgba(255, 255, 255, 0.08);
      border-color: rgba(255, 255, 255, 0.16);
    }

    .timer-opt.active {
      color: #fff;
      background: rgba(124, 92, 252, 0.22);
      border-color: var(--violet);
      font-weight: 600;
    }

    .timer-opt:disabled {
      opacity: 0.45;
      cursor: not-allowed;
    }

    .countdown-badge {
      margin-left: auto;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-family: 'DM Mono', monospace;
      font-size: 11px;
      font-weight: 600;
      color: var(--amber);
      background: rgba(245, 185, 77, 0.12);
      border: 1px solid rgba(245, 185, 77, 0.28);
      border-radius: 7px;
      padding: 4px 10px;
      white-space: nowrap;
    }

    .pulse-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--amber);
      display: inline-block;
      animation: pulseAnim 1.4s infinite ease-in-out;
    }

    @keyframes pulseAnim {
      0%, 100% { opacity: 1; transform: scale(1); }
      50% { opacity: 0.3; transform: scale(0.7); }
    }

    /* primary button */
    .primary-button {
      background: var(--violet);
      color: #fff;
      border-radius: 10px;
      padding: 10px 18px;
      font-size: 12px;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 7px;
      transition: opacity .15s;
    }

    .primary-button:active { opacity: .8; }
    .primary-button:disabled { opacity: .45; cursor: not-allowed; }

    .monitor-toggle { white-space: nowrap; }
    .monitor-toggle.paused { background: rgba(255,255,255,.07); color: var(--muted); }

    .button-dot {
      width: 7px; height: 7px;
      background: rgba(255,255,255,.6);
      border-radius: 50%;
      display: block;
    }

    /* ── Stats Row ── */
    .stats-row {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px;
      margin-bottom: 20px;
    }

    .stat-card {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 16px 18px;
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .stat-icon {
      width: 34px; height: 34px;
      border-radius: 10px;
      display: grid;
      place-items: center;
      font-size: 15px;
      flex-shrink: 0;
    }

    .stat-icon.violet { background: rgba(103,104,255,.12); color: var(--violet-d); }
    .stat-icon.mint   { background: rgba(39,211,155,.1);  color: var(--mint); }
    .stat-icon.amber  { background: rgba(245,185,77,.1);  color: var(--amber); }

    .stat-card > div span { font-size: 10px; color: var(--muted); display: block; margin-bottom: 4px; }
    .stat-card > div strong { font-size: 22px; font-weight: 700; line-height: 1; display: block; }
    .stat-card > div strong span { font-size: 11px; font-weight: 400; color: var(--muted); }

    small.trend { font-size: 9px; color: var(--muted); display: block; margin-top: 4px; }
    small.trend.up { color: var(--mint); }
    small.trend em { font-style: normal; color: var(--subtle); }

    /* ── Content Grid ── */
    .content-grid {
      display: grid;
      grid-template-columns: 1.4fr 1fr;
      gap: 16px;
    }

    /* ── Panels ── */
    .panel {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 20px 22px;
      min-width: 0;
      box-sizing: border-box;
    }

    .panel-heading {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 18px;
      gap: 10px;
      min-width: 0;
    }

    .section-eyebrow {
      font-size: 8px;
      font-weight: 700;
      letter-spacing: 1.4px;
      text-transform: uppercase;
      color: var(--subtle);
      display: block;
      margin-bottom: 4px;
    }

    .panel-heading h3 { font-size: 15px; font-weight: 700; }

    .text-button {
      font-size: 10px;
      color: var(--muted);
      display: flex;
      align-items: center;
      gap: 3px;
      transition: color .15s;
    }

    .text-button:hover { color: var(--text); }
    .text-button span  { color: var(--violet-d); }

    /* ── Activity List ── */
    .activity-list { display: flex; flex-direction: column; }

    .activity-item {
      display: grid;
      grid-template-columns: 36px 14px 1fr auto;
      align-items: start;
      min-height: 66px;
      gap: 0 8px;
    }

    .activity-time {
      font-size: 10px;
      font-family: 'DM Mono', monospace;
      color: var(--muted);
      padding-top: 4px;
      text-align: right;
    }

    .activity-line {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0;
    }

    .activity-dot {
      width: 10px; height: 10px;
      border-radius: 50%;
      flex-shrink: 0;
      margin-top: 4px;
    }

    .activity-dot.success { background: var(--mint); }
    .activity-dot.waiting { background: var(--amber); border: 2px solid rgba(245,185,77,.3); }

    .activity-line > span:nth-child(2) {
      display: block;
      flex: 1;
      width: 1px;
      background: var(--line);
      margin-top: 4px;
    }

    .activity-info { padding-left: 6px; padding-top: 2px; }
    .activity-info strong { font-size: 12px; display: block; margin-bottom: 5px; }
    .activity-info p { display: flex; align-items: center; gap: 6px; font-size: 9px; color: var(--muted); }

    .activity-result { font-size: 10px; padding-top: 4px; white-space: nowrap; }
    .success-text { color: var(--mint); }
    .waiting-text { color: var(--amber); }

    /* ── Tags ── */
    .tag {
      font-size: 9px;
      font-weight: 600;
      padding: 2px 7px;
      border-radius: 4px;
      display: inline-block;
    }

    .tag.number { background: rgba(103,104,255,.12); color: var(--violet-d); }
    .tag.radar  { background: rgba(39,211,155,.1);  color: var(--mint); }
    .tag.qr     { background: rgba(245,185,77,.1);  color: var(--amber); }

    /* ── Upcoming Panel ── */
    .upcoming-list { display: flex; flex-direction: column; gap: 4px; }

    .upcoming-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 12px;
      border-radius: 12px;
    }

    .upcoming-item.current { background: rgba(103,104,255,.07); }

    .day-box {
      width: 38px; height: 44px;
      background: var(--surface2);
      border-radius: 10px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .day-box span { font-size: 8px; color: var(--muted); }
    .day-box strong { font-size: 15px; font-weight: 700; }

    .upcoming-info { flex: 1; }
    .upcoming-info strong { font-size: 12px; display: block; }
    .upcoming-info span   { font-size: 9px; color: var(--muted); font-family: 'DM Mono', monospace; }

    .round-button {
      width: 28px; height: 28px;
      border-radius: 50%;
      background: rgba(103,104,255,.12);
      color: var(--violet-d);
      font-size: 13px;
      display: grid;
      place-items: center;
    }

    .outline-button {
      width: 100%;
      margin-top: 12px;
      padding: 10px;
      border: 1px solid var(--line);
      border-radius: 10px;
      font-size: 11px;
      color: var(--muted);
      text-align: center;
      transition: border-color .15s, color .15s;
    }

    .outline-button:hover { border-color: rgba(255,255,255,.15); color: var(--text); }
    .outline-button span { color: var(--violet-d); }

    /* ── Schedule View ── */
    .schedule-summary {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
      margin-bottom: 20px;
    }

    .schedule-summary > div {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px 16px;
    }

    .schedule-summary span { font-size: 9px; color: var(--muted); display: block; margin-bottom: 6px; }
    .schedule-summary strong { font-size: 20px; font-weight: 700; }
    .schedule-summary strong small { font-size: 10px; font-weight: 400; color: var(--muted); margin-left: 2px; }

    .mint-text { color: var(--mint); }

    .summary-progress { grid-column: span 2; display: flex; flex-direction: column; justify-content: center; gap: 8px; }
    .summary-progress > div { display: flex; justify-content: space-between; align-items: baseline; }
    .summary-progress > div span { font-size: 9px; color: var(--muted); }
    .summary-progress > div strong { font-size: 13px; }

    .progress-track {
      height: 4px;
      background: rgba(255,255,255,.06);
      border-radius: 4px;
      overflow: hidden;
    }

    .progress-track span {
      display: block;
      height: 100%;
      width: 72%;
      background: linear-gradient(90deg, var(--violet), var(--mint));
      border-radius: 4px;
    }

    /* Week Selector */
    .week-selector {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 8px 0 18px;
    }

    .week-arrow {
      font-size: 22px;
      color: var(--subtle);
      padding: 4px 6px;
    }

    .day-selector {
      flex: 1;
      height: 58px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 4px;
      border-radius: 12px;
      color: var(--muted);
      transition: background .15s, color .15s;
    }

    .day-selector:hover { background: rgba(255,255,255,.04); }
    .day-selector.active { background: var(--violet); color: #fff; }
    .day-selector.muted { opacity: .45; }

    .day-selector span  { font-size: 10px; }
    .day-selector strong { font-size: 15px; font-weight: 700; }

    /* ── Schedule Presets & Time Picker Enhancements ── */
    .auto-schedule-banner {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 16px;
      padding: 14px 18px;
      background: linear-gradient(135deg, rgba(124,92,252,.12) 0%, rgba(20,23,36,0.95) 100%);
      border: 1px solid rgba(124,92,252,.25);
      border-radius: 18px;
      min-width: 0;
      box-sizing: border-box;
    }

    .auto-schedule-inner {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
      flex: 1;
    }

    .auto-schedule-icon {
      width: 36px;
      height: 36px;
      border-radius: 10px;
      background: rgba(124,92,252,.18);
      color: var(--violet-d);
      display: grid;
      place-items: center;
      font-size: 16px;
      flex-shrink: 0;
    }

    .auto-schedule-text {
      min-width: 0;
      flex: 1;
    }

    .auto-schedule-title-row {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .auto-schedule-text p {
      font-size: 10px;
      color: var(--muted);
      margin-top: 3px;
      line-height: 1.45;
    }

    .auto-badge {
      font-size: 9px;
      font-weight: 600;
      padding: 2px 7px;
      border-radius: 4px;
      display: inline-block;
    }
    .auto-badge.on {
      background: rgba(39,211,155,.15);
      color: var(--mint);
      border: 1px solid rgba(39,211,155,.3);
    }
    .auto-badge.off {
      background: rgba(255,255,255,.05);
      color: var(--subtle);
      border: 1px solid var(--line);
    }

    .schedule-presets-bar {
      display: flex;
      align-items: center;
      gap: 6px;
      margin-bottom: 12px;
      flex-wrap: wrap;
    }

    .presets-label {
      font-size: 10px;
      color: var(--subtle);
      margin-right: 2px;
      white-space: nowrap;
    }

    @media (min-width: 701px) {
      .preset-chip-right { margin-left: auto; }
    }

    .preset-chip {
      font-size: 10.5px;
      padding: 4px 9px;
      border-radius: 6px;
      background: rgba(255,255,255,.03);
      border: 1px solid var(--line);
      color: var(--muted);
      cursor: pointer;
      transition: all .15s;
      user-select: none;
    }
    .preset-chip:hover {
      background: rgba(124,92,252,.15);
      border-color: var(--violet);
      color: #fff;
    }

    .time-range-picker {
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }

    .time-field {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      background: #090e1a;
      border: 1px solid var(--line);
      border-radius: 7px;
      padding: 3px 7px;
      transition: border-color .15s;
    }
    .time-field:focus-within {
      border-color: var(--violet);
      box-shadow: 0 0 8px rgba(124,92,252,.25);
    }
    .time-field-label {
      font-size: 9px;
      color: var(--subtle);
      font-weight: 500;
    }

    .time-picker {
      background: transparent;
      border: none;
      color: var(--text);
      font-family: 'DM Mono', monospace;
      font-size: 11.5px;
      font-weight: 600;
      outline: none;
      cursor: pointer;
      width: 86px;
    }
    .time-picker::-webkit-calendar-picker-indicator {
      filter: invert(0.8) hue-rotate(180deg);
      cursor: pointer;
      opacity: 0.6;
    }
    .time-picker::-webkit-calendar-picker-indicator:hover {
      opacity: 1;
    }

    .time-sep {
      color: var(--subtle);
      font-size: 11px;
      font-weight: 600;
    }

    .day-badge-col {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .day-name {
      font-size: 11px;
      font-weight: 600;
      color: var(--text);
    }
    .day-type-tag {
      font-size: 8.5px;
      color: var(--subtle);
    }
    .day-type-tag.weekend {
      color: var(--amber);
    }

    .duration-badge {
      font-size: 10px;
      font-family: 'DM Mono', monospace;
      color: var(--violet-d);
      background: rgba(124,92,252,.12);
      border-radius: 5px;
      padding: 2px 7px;
      font-weight: 600;
      white-space: nowrap;
    }
    .duration-badge.off {
      color: var(--subtle);
      background: rgba(255,255,255,.04);
    }

    .schedule-table-wrapper {
      width: 100%;
      overflow-x: hidden;
    }
    .schedule-table {
      width: 100%;
      border-collapse: collapse;
    }

    .schedule-row {
      border-bottom: 1px solid rgba(255,255,255,.03);
      transition: opacity .15s;
    }
    .schedule-row:last-child {
      border-bottom: none;
    }
    .schedule-row.disabled {
      opacity: 0.42;
    }
    .schedule-row.disabled .time-field {
      border-color: rgba(255,255,255,.03);
      background: rgba(255,255,255,.02);
    }

    /* Schedule layout */
    .schedule-layout {
      display: grid;
      grid-template-columns: 1.4fr 1fr;
      gap: 16px;
    }

    .count-badge {
      font-size: 9px;
      font-weight: 700;
      background: rgba(103,104,255,.15);
      color: var(--violet-d);
      border-radius: 20px;
      padding: 2px 9px;
    }

    .course-card {
      display: grid;
      grid-template-columns: 48px 4px 1fr;
      gap: 0 10px;
      margin-bottom: 12px;
      align-items: start;
    }

    .course-time { text-align: right; padding-top: 2px; }
    .course-time strong { font-size: 12px; font-weight: 700; display: block; font-family: 'DM Mono', monospace; }
    .course-time span   { font-size: 9px; color: var(--muted); display: block; margin-top: 2px; font-family: 'DM Mono', monospace; }

    .course-bar {
      background: var(--line);
      border-radius: 2px;
      align-self: stretch;
      min-height: 60px;
    }

    .course-card.now .course-bar { background: var(--mint); }
    .course-card.upcoming .course-bar { background: var(--violet); }

    .course-content {
      background: var(--surface2);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px 14px;
    }

    .course-title-row {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 8px;
    }

    .course-title-row h4 { font-size: 13px; font-weight: 600; }
    .course-title-row p  { font-size: 10px; color: var(--muted); margin-top: 2px; }

    .status-label {
      font-size: 9px;
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 6px;
      white-space: nowrap;
      flex-shrink: 0;
    }

    .status-label.done { background: rgba(39,211,155,.1); color: var(--mint); }
    .status-label.next { background: rgba(245,185,77,.1); color: var(--amber); }

    .course-meta {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 10px;
      font-size: 9px;
      color: var(--subtle);
    }

    .course-more { margin-left: auto; color: var(--subtle); letter-spacing: 1px; }

    /* Quick settings (schedule page sidebar) */
    .setting-row {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 14px 0;
      border-bottom: 1px solid var(--line);
    }

    .setting-row:last-child { border-bottom: 0; }
    .setting-row > div { flex: 1; }
    .setting-row strong { font-size: 11px; display: block; }
    .setting-row span   { font-size: 9px; color: var(--subtle); display: block; margin-top: 3px; }

    /* ── Settings View ── */
    .settings-layout {
      display: grid;
      grid-template-columns: 1.15fr .85fr;
      gap: 16px;
    }

    .account-panel { grid-row: span 2; }

    .profile-banner {
      display: flex;
      align-items: center;
      gap: 14px;
      padding: 16px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: rgba(103,104,255,.05);
      margin-bottom: 20px;
    }

    .large-avatar {
      width: 48px; height: 48px;
      border-radius: 14px;
      background: linear-gradient(135deg, var(--violet), #9c6bff);
      font-size: 14px;
      font-weight: 700;
      display: grid;
      place-items: center;
      flex-shrink: 0;
    }

    .profile-banner strong { font-size: 14px; display: block; }
    .profile-banner span   { font-family: 'DM Mono', monospace; font-size: 10px; color: #a5a0ff; display: block; margin-top: 3px; }
    .profile-banner small  { font-size: 9px; color: var(--muted); display: block; margin-top: 4px; }

    .edit-icon { margin-left: auto; font-size: 17px; color: var(--muted); }
    .edit-icon:hover { color: var(--text); }

    /* Account form */
    .form-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px 12px;
    }

    .form-grid label > span {
      display: block;
      font-size: 10px;
      color: var(--muted);
      margin-bottom: 6px;
    }

    .form-field {
      height: 41px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 12px;
      background: #0c1424;
      border: 1px solid var(--line);
      border-radius: 9px;
      font-size: 11px;
      color: var(--text);
      transition: border-color .15s;
    }

    .form-field input,
    .form-field select {
      background: none;
      border: none;
      outline: none;
      color: var(--text);
      font-size: 11px;
      width: 100%;
    }

    .form-field select option { background: #0c1424; }
    .form-field.focused { border-color: var(--violet); }

    .show-pw-btn {
      color: var(--violet-d);
      font-size: 10px;
      flex-shrink: 0;
      margin-left: 6px;
    }

    .connected-badge {
      display: flex;
      align-items: center;
      gap: 6px;
      color: var(--mint);
      font-size: 11px;
    }

    .connected-badge span {
      width: 6px; height: 6px;
      background: var(--mint);
      border-radius: 50%;
    }

    .primary-button.full { width: 100%; justify-content: center; margin-top: 20px; }

    /* Preferences */
    .preference-row {
      display: flex;
      align-items: center;
      gap: 11px;
      padding: 14px 0;
      border-bottom: 1px solid var(--line);
    }

    .preference-row:last-child { border-bottom: 0; }

    .preference-icon {
      width: 30px; height: 30px;
      display: grid;
      place-items: center;
      background: rgba(103,104,255,.11);
      border-radius: 9px;
      color: var(--violet-d);
      flex-shrink: 0;
    }

    .preference-row > div:nth-child(2) { flex: 1; }
    .preference-row strong { font-size: 11px; display: block; }
    .preference-row span   { font-size: 9px; color: var(--subtle); display: block; margin-top: 3px; }

    .connected-label {
      font-size: 10px;
      color: var(--mint);
      display: flex;
      align-items: center;
      gap: 5px;
    }

    .connected-label span {
      width: 6px; height: 6px;
      background: var(--mint);
      border-radius: 50%;
      display: inline-block;
    }

    .saved-label {
      font-size: 10px;
      color: var(--mint);
      display: flex;
      align-items: center;
      gap: 5px;
    }

    .saved-label span {
      width: 6px; height: 6px;
      background: var(--mint);
      border-radius: 50%;
      display: inline-block;
    }

    .settings-symbol { color: var(--violet-d); font-size: 18px; }

    /* Danger Panel */
    .danger-panel {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      padding: 16px 20px;
    }

    .danger-panel strong { font-size: 11px; display: block; }
    .danger-panel span   { font-size: 9px; color: var(--subtle); display: block; margin-top: 4px; }

    .danger-button {
      background: rgba(255,104,124,.08);
      border: 1px solid rgba(255,104,124,.2);
      color: #ff8796;
      border-radius: 8px;
      padding: 8px 12px;
      font-size: 10px;
      white-space: nowrap;
      transition: background .15s;
    }

    .danger-button:hover { background: rgba(255,104,124,.14); }

    /* ── Toggle Switch ── */
    .switch {
      width: 35px; height: 20px;
      padding: 3px;
      background: #303b52;
      border-radius: 20px;
      transition: background .2s;
      flex-shrink: 0;
    }

    .switch > span {
      display: block;
      width: 14px; height: 14px;
      background: #77839a;
      border-radius: 50%;
      transition: transform .2s, background .2s;
    }

    .switch.on { background: var(--violet); }
    .switch.on > span { transform: translateX(15px); background: #fff; }

    /* ── Setup Alert Banner ── */
    .setup-alert {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 12px 16px;
      margin-bottom: 16px;
      background: rgba(255, 179, 64, 0.08);
      border: 1px solid rgba(255, 179, 64, 0.28);
      border-radius: 12px;
    }
    .setup-alert-left {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }
    .setup-alert-icon { font-size: 20px; flex-shrink: 0; }
    .setup-alert strong { font-size: 13px; color: #ffb340; display: block; }
    .setup-alert span { font-size: 11px; color: var(--muted); display: block; margin-top: 2px; }
    .setup-alert-btn {
      padding: 7px 14px;
      background: #ffb340;
      color: #0b0f19;
      font-weight: 700;
      font-size: 11px;
      border-radius: 8px;
      border: none;
      cursor: pointer;
      white-space: nowrap;
      flex-shrink: 0;
      transition: opacity .15s;
    }
    .setup-alert-btn:hover { opacity: 0.88; }

    /* ── Toast ── */
    .toast {
      position: fixed;
      z-index: 30;
      right: 24px; bottom: 24px;
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 13px 16px;
      border: 1px solid rgba(39,211,155,.28);
      border-radius: 12px;
      background: #152a2a;
      box-shadow: var(--shadow);
      transform: translateY(20px);
      opacity: 0;
      pointer-events: none;
      transition: .25s;
    }

    .toast.show { transform: translateY(0); opacity: 1; }
    .toast > span { color: var(--mint); font-size: 16px; }
    .toast strong { font-size: 11px; }
    .toast small  { color: #86a59f; font-size: 10px; }

    /* ── Bottom Nav (mobile only) ── */
    .bottom-nav { display: none; }

    /* ── Responsive ── */
    @media (max-width: 900px) {
      .sidebar { width: 200px; }
      .main-content { margin-left: 200px; }
      .content-grid, .schedule-layout, .settings-layout { grid-template-columns: 1fr; }
      .account-panel { grid-row: auto; }
      .schedule-summary { grid-template-columns: 1fr 1fr; }
      .summary-progress { grid-column: span 2; }
      .stats-row { grid-template-columns: repeat(3, 1fr); }
    }

    @media (max-width: 700px) {
      .sidebar { display: none; }
      .main-content {
        margin-left: 0;
        padding-bottom: 72px;
        width: 100%;
        max-width: 100vw;
        overflow-x: hidden;
      }
      .topbar {
        height: 54px;
        padding: 0 14px;
        width: 100%;
        box-sizing: border-box;
      }
      .breadcrumb { display: none; }
      .mobile-brand { display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 700; }
      .mobile-menu  { display: block; font-size: 18px; color: var(--muted); }
      .top-actions { gap: 8px; flex-shrink: 0; }
      .view {
        padding: 18px 12px 32px;
        width: 100%;
        max-width: 100%;
        box-sizing: border-box;
        overflow-x: hidden;
      }
      .panel {
        padding: 14px 14px;
        border-radius: 14px;
        width: 100%;
        box-sizing: border-box;
      }
      .panel-heading {
        margin-bottom: 14px;
      }
      .page-heading {
        margin-bottom: 18px;
        gap: 8px;
      }
      .page-heading h1 { font-size: 22px; }
      .page-heading.compact h1 { font-size: 19px; }
      .stats-row { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 6px; }
      .stat-card {
        padding: 8px 6px;
        gap: 6px;
        flex-direction: column;
        align-items: flex-start;
        min-width: 0;
        overflow: hidden;
      }
      .stat-card > div {
        min-width: 0;
        width: 100%;
      }
      .stat-card > div strong {
        font-size: 15px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .stat-card > div span {
        font-size: 9px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .stat-card small {
        font-size: 8px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        display: block;
      }
      .stat-icon { width: 26px; height: 26px; font-size: 11px; flex-shrink: 0; }
      .content-grid, .schedule-layout, .settings-layout { grid-template-columns: minmax(0, 1fr); gap: 12px; }
      .account-panel { grid-row: auto; }
      .schedule-summary { grid-template-columns: repeat(2, minmax(0, 1fr)); margin-bottom: 14px; gap: 8px; }
      .schedule-summary > div { padding: 10px 12px; min-width: 0; }
      .schedule-summary strong { font-size: 16px; }
      .summary-progress { grid-column: span 2; }
      .form-grid { grid-template-columns: minmax(0, 1fr); }
      .monitor-card { padding: 16px 14px; border-radius: 16px; }
      .monitor-main { min-height: auto; padding: 6px 0 10px; }
      .monitor-main > div:first-child { min-width: 0; flex: 1; }
      .monitor-main h2 { font-size: 16px; max-width: 100%; }
      .monitor-main p { font-size: 10.5px; max-width: 100%; }
      .radar-orb { width: 64px; height: 64px; margin-left: 8px; flex-shrink: 0; }
      .monitor-bottom { flex-wrap: wrap; gap: 10px; }
      .timer-row { flex-wrap: wrap; gap: 6px; }
      .timer-options { flex-wrap: wrap; gap: 5px; }
      .timer-opt { font-size: 10px; padding: 4px 8px; }
      .countdown-badge { font-size: 10px; padding: 3px 8px; }
      .schedule-presets-bar {
        gap: 5px;
        margin-bottom: 12px;
      }
      .schedule-presets-bar .preset-chip {
        margin-left: 0 !important;
        font-size: 10px;
        padding: 4px 7px;
      }
      .auto-schedule-banner {
        padding: 12px 14px;
        gap: 10px;
      }
      .auto-schedule-inner {
        gap: 10px;
      }
      .bottom-nav {
        position: fixed;
        display: flex;
        z-index: 20;
        left: 0; right: 0; bottom: 0;
        height: 60px;
        background: rgba(11,16,31,.95);
        border-top: 1px solid var(--line);
        backdrop-filter: blur(18px);
        justify-content: space-around;
        padding: 4px 8px;
        width: 100%;
        max-width: 100vw;
        box-sizing: border-box;
      }
      .bottom-nav .nav-item {
        flex: 1;
        max-width: 110px;
        min-width: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 2px;
        padding: 5px 4px;
        font-size: 9.5px;
        border-radius: 10px;
        color: var(--muted);
      }
      .bottom-nav .nav-item.active { background: rgba(103,104,255,.13); color: var(--violet-d); }
      .bottom-nav .nav-icon { font-size: 17px; }
      .toast { left: 14px; right: 14px; bottom: 74px; }
    }

    @media (max-width: 650px) {
      .schedule-table-wrapper {
        width: 100%;
        overflow-x: hidden;
      }
      .schedule-table,
      .schedule-table tbody {
        display: block;
        width: 100%;
      }
      .schedule-row {
        display: flex !important;
        flex-wrap: wrap;
        align-items: center;
        justify-content: space-between;
        padding: 10px 12px !important;
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid var(--line);
        border-radius: 12px;
        margin-bottom: 8px;
        gap: 6px 0;
        box-sizing: border-box;
        width: 100%;
      }
      .schedule-row:last-child {
        margin-bottom: 0;
      }
      /* td 1: Day badge */
      .schedule-row td:nth-child(1) {
        order: 1;
        display: flex;
        align-items: center;
        width: auto !important;
        padding: 0 !important;
      }
      .schedule-row .day-badge-col {
        flex-direction: row;
        align-items: center;
        gap: 6px;
      }
      .day-name {
        font-size: 12px;
      }
      .day-type-tag {
        font-size: 8.5px;
        padding: 1px 5px;
        border-radius: 4px;
        background: rgba(255,255,255,.04);
      }
      /* td 3: Duration badge */
      .schedule-row td:nth-child(3) {
        order: 2;
        display: flex;
        align-items: center;
        width: auto !important;
        text-align: left !important;
        padding: 0 0 0 8px !important;
        flex: 1;
      }
      /* td 4: Switch */
      .schedule-row td:nth-child(4) {
        order: 3;
        display: flex;
        align-items: center;
        justify-content: flex-end;
        width: auto !important;
        padding: 0 !important;
      }
      /* td 2: Time range picker */
      .schedule-row td:nth-child(2) {
        order: 4;
        display: block;
        width: 100% !important;
        padding: 5px 0 0 0 !important;
      }
      .time-range-picker {
        display: flex;
        align-items: center;
        width: 100%;
        gap: 6px;
      }
      .time-field {
        flex: 1;
        min-width: 0;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 4px 8px;
        background: #090e1a;
      }
      .time-picker {
        width: 100%;
        min-width: 0;
        font-size: 12px;
        text-align: right;
      }
      .time-sep {
        flex-shrink: 0;
        font-size: 12px;
        padding: 0 2px;
      }
    }
  </style>
</head>
<body>
<div class="app-shell">

  <!-- ── Sidebar ── -->
  <aside class="sidebar" aria-label="主要導覽">
    <div class="brand">
      <div class="brand-mark" aria-hidden="true"><span></span><span></span><span></span></div>
      <div>
        <strong>iClass</strong>
        <small>自動簽到助手</small>
      </div>
    </div>
    <div class="sidebar-label">工作區</div>
    <nav class="side-nav">
      <button class="nav-item active" data-view="dashboard"><span class="nav-icon">⌂</span><span>控制台</span></button>
      <button class="nav-item" data-view="schedule"><span class="nav-icon">◷</span><span>上課排程</span></button>
      <button class="nav-item" data-view="settings"><span class="nav-icon">⚙</span><span>帳號設定</span></button>
    </nav>
    <div class="sidebar-bottom">
      <div class="mini-account">
        <div class="avatar" id="sidebarAvatar">--</div>
        <div>
          <strong id="sidebarSchool">--</strong>
          <span id="sidebarUser">未設定</span>
        </div>
        <span class="online-dot" id="sidebarOnline" style="background: var(--subtle);"></span>
      </div>
      <div class="sidebar-note"><span class="pulse-dot"></span> Web GUI 模式</div>
    </div>
  </aside>

  <!-- ── Main ── -->
  <main class="main-content">
    <header class="topbar">
      <div class="mobile-brand">
        <div class="brand-mark" aria-hidden="true"><span></span><span></span><span></span></div>
        <strong>iClass</strong>
      </div>
      <div class="breadcrumb">
        <span>工作區</span>
        <span class="slash">/</span>
        <strong id="breadcrumb-title">控制台</strong>
      </div>
      <div class="top-actions">
        <span class="demo-badge">LIVE</span>
        <button class="mobile-menu" aria-label="選單">☰</button>
      </div>
    </header>

    <!-- ═══════ Dashboard View ═══════ -->
    <section class="view active" id="dashboard-view">
      <div class="page-heading">
        <div>
          <p class="eyebrow" id="todayLabel">--</p>
          <h1>自動簽到<span style="color:var(--violet-d);">助手</span></h1>
          <p class="heading-copy" id="dashSubtitle">監控中，等待下一堂課程點名。</p>
        </div>
        <div class="heading-time">
          <span>現在時間</span>
          <strong id="live-time">--:--</strong>
        </div>
      </div>

      <!-- Setup Alert Banner -->
      <div id="setupAlert" class="setup-alert" style="display:none;">
        <div class="setup-alert-left">
          <span class="setup-alert-icon">⚠️</span>
          <div>
            <strong>尚未設定學校登入帳號</strong>
            <span>請先填寫學號與密碼，完成後即可啟動自動簽到監控。</span>
          </div>
        </div>
        <button type="button" class="setup-alert-btn" id="goSettingsBtn">立即前往設定 →</button>
      </div>

      <!-- Monitor Card -->
      <div class="monitor-card">
        <div class="monitor-glow"></div>
        <div class="monitor-topline">
          <span class="status-pill" id="statusPill">
            <span></span><span id="monitorStatusText">已停止</span>
          </span>
          <button class="more-button" aria-label="更多">•••</button>
        </div>
        <div class="monitor-main">
          <div>
            <span class="card-kicker">目前狀態</span>
            <h2 id="monitorTitle">監控尚未啟動</h2>
            <p id="monitorDesc">請設定帳號後按下啟動按鈕，開始自動簽到監控。</p>
          </div>
          <div class="radar-orb" aria-hidden="true">
            <div class="orb-ring ring-one"></div>
            <div class="orb-ring ring-two"></div>
            <div class="orb-core"><span></span></div>
          </div>
        </div>
        <!-- Timer row -->
        <div id="timerRow" class="timer-row">
          <div class="timer-label">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="opacity:0.6;"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
            <span>定時停止</span>
          </div>
          <div class="timer-options" id="timerOptions">
            <button class="timer-opt active" data-min="0">不限</button>
            <button class="timer-opt" data-min="30">30 分</button>
            <button class="timer-opt" data-min="60">1 小時</button>
            <button class="timer-opt" data-min="120">2 小時</button>
            <button class="timer-opt" data-min="180">3 小時</button>
            <button class="timer-opt" id="customTimerBtn" data-min="-1">自訂</button>
            <div id="customTimerWrap" style="display:none;align-items:center;gap:4px;">
              <input type="number" id="customTimerInput" min="1" max="1440" placeholder="分" style="width:48px;padding:3px 6px;border-radius:6px;border:1px solid var(--violet);background:#101322;color:var(--text);font-size:11px;outline:none;text-align:center;">
              <span style="font-size:10px;color:var(--muted);">分鐘</span>
            </div>
          </div>
          <div id="countdownBadge" class="countdown-badge" style="display:none;">
            <span class="pulse-dot"></span>
            <span id="countdownText">⏱ --:--</span>
          </div>
        </div>
        <div class="monitor-bottom" style="border-top:none;margin-top:12px;padding-top:0;">
          <div class="status-metrics">
            <div><span>檢查次數</span><strong id="checkCount">0</strong></div>
            <div><span>執行階段</span><strong id="phaseText" class="mode-text">休眠中</strong></div>
          </div>
          <button class="primary-button monitor-toggle" id="toggleBtn">
            <span class="button-dot"></span>
            <span id="toggleLabel">啟動監控</span>
          </button>
        </div>
      </div>

      <!-- Stat Cards -->
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-icon violet">↗</div>
          <div>
            <span>監控狀態</span>
            <strong id="statStatus" style="font-size:16px;">停止中</strong>
            <small class="trend">點擊啟動按鈕開始</small>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon mint">✓</div>
          <div>
            <span>本次已查</span>
            <strong id="statChecks">0<span> 次</span></strong>
            <small>本次啟動後累計</small>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon amber">◷</div>
          <div>
            <span>執行狀態</span>
            <strong id="statPhase" style="font-size:14px;">待機</strong>
            <small id="statDetail">尚未啟動</small>
          </div>
        </div>
      </div>

      <!-- Content Grid: Log + Upcoming -->
      <div class="content-grid">
        <!-- Activity / Log -->
        <div class="panel activity-panel">
          <div class="panel-heading">
            <div>
              <span class="section-eyebrow">LIVE ACTIVITY</span>
              <h3>即時執行紀錄</h3>
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
              <input type="text" id="logFilter" placeholder="搜尋..." style="height:26px;background:rgba(255,255,255,.04);border:1px solid var(--line);border-radius:6px;padding:0 8px;color:var(--text);font-size:10px;outline:none;width:90px;font-family:inherit;">
            </div>
          </div>
          <div id="consoleBox" style="height:210px;overflow-y:auto;font-family:'DM Mono',monospace;font-size:10.5px;line-height:1.6;color:var(--muted);display:flex;flex-direction:column;gap:2px;">
            <span style="color:var(--subtle);">尚無執行紀錄</span>
          </div>
        </div>

        <!-- Upcoming Schedule Preview -->
        <div class="panel week-panel">
          <div class="panel-heading">
            <div>
              <span class="section-eyebrow">UPCOMING</span>
              <h3>接下來的排程</h3>
            </div>
            <button class="round-button" data-view="schedule" aria-label="查看排程">↗</button>
          </div>
          <div class="upcoming-list" id="upcomingList">
            <div style="font-size:10px;color:var(--subtle);padding:8px 0;">請前往「排程」頁面設定上課時間。</div>
          </div>
          <button class="outline-button" data-view="schedule">管理完整排程 <span>→</span></button>
        </div>
      </div>
    </section>

    <!-- ═══════ Schedule View ═══════ -->
    <section class="view" id="schedule-view">
      <div class="page-heading compact">
        <div>
          <p class="eyebrow">自動化設定</p>
          <h1>上課排程</h1>
          <p class="heading-copy">設定每週自動監控的時段。</p>
        </div>
      </div>

      <!-- Auto Schedule Master Banner -->
      <div class="panel auto-schedule-banner">
        <div class="auto-schedule-inner">
          <div class="auto-schedule-icon">⏱</div>
          <div class="auto-schedule-text">
            <div class="auto-schedule-title-row">
              <strong style="font-size:13px;">依排程自動開啟監控</strong>
              <span id="autoScheduleBadge" class="auto-badge on">● 守候中</span>
            </div>
            <p>抵達每日排程的上課開始時間時，背景將自動開啟點名監控；超出時段自動休眠，省去手動啟動的繁瑣。</p>
          </div>
        </div>
        <button class="switch on" id="autoScheduleSwitch" aria-label="依排程自動開啟監控"><span></span></button>
      </div>

      <!-- Summary -->
      <div class="schedule-summary">
        <div><span>啟用天數</span><strong id="schedEnabledDays">0 <small>天</small></strong></div>
        <div><span>今日時段</span><strong id="schedTodaySlot" style="font-size:14px;">08:00–18:00</strong></div>
        <div class="summary-progress">
          <div><span>本週涵蓋率</span><strong id="schedCoverage">0%</strong></div>
          <div class="progress-track"><span id="schedProgressBar" style="width:0%"></span></div>
        </div>
      </div>

      <div class="schedule-layout">
        <!-- Schedule list -->
        <div class="panel schedule-list-panel">
          <div class="panel-heading">
            <div>
              <span class="section-eyebrow">WEEKLY SCHEDULE</span>
              <h3>每日時段設定</h3>
            </div>
            <button class="primary-button" id="saveScheduleBtn" style="padding:7px 14px;font-size:11px;">儲存排程</button>
          </div>

          <!-- Presets -->
          <div class="schedule-presets-bar">
            <span class="presets-label">快速套用：</span>
            <button class="preset-chip" data-preset="weekday_full">平日 08:00~18:00</button>
            <button class="preset-chip" data-preset="morning">上午 08:00~12:00</button>
            <button class="preset-chip" data-preset="afternoon">下午 13:00~18:00</button>
            <button class="preset-chip" data-preset="night">夜間 18:00~22:00</button>
            <button class="preset-chip" data-preset="all_day">全天 08:00~22:00</button>
            <button class="preset-chip preset-chip-right" data-preset="weekdays_only">僅開平日</button>
            <button class="preset-chip" data-preset="all_on">全週開啟</button>
          </div>

          <div class="schedule-table-wrapper">
            <table class="schedule-table">
              <tbody id="scheduleTableBody">
                <tr data-day="0" class="schedule-row">
                  <td style="width:58px;padding:9px 0 9px 2px;"><div class="day-badge-col"><span class="day-name">週一</span><span class="day-type-tag">平日</span></div></td>
                  <td><div class="time-range-picker"><div class="time-field"><span class="time-field-label">開始</span><input type="time" class="time-picker start-time" value="08:00"></div><span class="time-sep">～</span><div class="time-field"><span class="time-field-label">結束</span><input type="time" class="time-picker end-time" value="18:00"></div></div></td>
                  <td style="text-align:right;padding-right:10px;"><span class="duration-badge">10 小時</span></td>
                  <td style="width:46px;text-align:right;"><button class="switch on" aria-label="週一"><span></span></button></td>
                </tr>
                <tr data-day="1" class="schedule-row">
                  <td style="width:58px;padding:9px 0 9px 2px;"><div class="day-badge-col"><span class="day-name">週二</span><span class="day-type-tag">平日</span></div></td>
                  <td><div class="time-range-picker"><div class="time-field"><span class="time-field-label">開始</span><input type="time" class="time-picker start-time" value="08:00"></div><span class="time-sep">～</span><div class="time-field"><span class="time-field-label">結束</span><input type="time" class="time-picker end-time" value="18:00"></div></div></td>
                  <td style="text-align:right;padding-right:10px;"><span class="duration-badge">10 小時</span></td>
                  <td style="width:46px;text-align:right;"><button class="switch on" aria-label="週二"><span></span></button></td>
                </tr>
                <tr data-day="2" class="schedule-row">
                  <td style="width:58px;padding:9px 0 9px 2px;"><div class="day-badge-col"><span class="day-name">週三</span><span class="day-type-tag">平日</span></div></td>
                  <td><div class="time-range-picker"><div class="time-field"><span class="time-field-label">開始</span><input type="time" class="time-picker start-time" value="08:00"></div><span class="time-sep">～</span><div class="time-field"><span class="time-field-label">結束</span><input type="time" class="time-picker end-time" value="18:00"></div></div></td>
                  <td style="text-align:right;padding-right:10px;"><span class="duration-badge">10 小時</span></td>
                  <td style="width:46px;text-align:right;"><button class="switch on" aria-label="週三"><span></span></button></td>
                </tr>
                <tr data-day="3" class="schedule-row">
                  <td style="width:58px;padding:9px 0 9px 2px;"><div class="day-badge-col"><span class="day-name">週四</span><span class="day-type-tag">平日</span></div></td>
                  <td><div class="time-range-picker"><div class="time-field"><span class="time-field-label">開始</span><input type="time" class="time-picker start-time" value="08:00"></div><span class="time-sep">～</span><div class="time-field"><span class="time-field-label">結束</span><input type="time" class="time-picker end-time" value="18:00"></div></div></td>
                  <td style="text-align:right;padding-right:10px;"><span class="duration-badge">10 小時</span></td>
                  <td style="width:46px;text-align:right;"><button class="switch on" aria-label="週四"><span></span></button></td>
                </tr>
                <tr data-day="4" class="schedule-row">
                  <td style="width:58px;padding:9px 0 9px 2px;"><div class="day-badge-col"><span class="day-name">週五</span><span class="day-type-tag">平日</span></div></td>
                  <td><div class="time-range-picker"><div class="time-field"><span class="time-field-label">開始</span><input type="time" class="time-picker start-time" value="08:00"></div><span class="time-sep">～</span><div class="time-field"><span class="time-field-label">結束</span><input type="time" class="time-picker end-time" value="18:00"></div></div></td>
                  <td style="text-align:right;padding-right:10px;"><span class="duration-badge">10 小時</span></td>
                  <td style="width:46px;text-align:right;"><button class="switch on" aria-label="週五"><span></span></button></td>
                </tr>
                <tr data-day="5" class="schedule-row">
                  <td style="width:58px;padding:9px 0 9px 2px;"><div class="day-badge-col"><span class="day-name">週六</span><span class="day-type-tag weekend">週末</span></div></td>
                  <td><div class="time-range-picker"><div class="time-field"><span class="time-field-label">開始</span><input type="time" class="time-picker start-time" value="08:00"></div><span class="time-sep">～</span><div class="time-field"><span class="time-field-label">結束</span><input type="time" class="time-picker end-time" value="18:00"></div></div></td>
                  <td style="text-align:right;padding-right:10px;"><span class="duration-badge off">休眠</span></td>
                  <td style="width:46px;text-align:right;"><button class="switch" aria-label="週六"><span></span></button></td>
                </tr>
                <tr data-day="6" class="schedule-row">
                  <td style="width:58px;padding:9px 0 9px 2px;"><div class="day-badge-col"><span class="day-name">週日</span><span class="day-type-tag weekend">週末</span></div></td>
                  <td><div class="time-range-picker"><div class="time-field"><span class="time-field-label">開始</span><input type="time" class="time-picker start-time" value="08:00"></div><span class="time-sep">～</span><div class="time-field"><span class="time-field-label">結束</span><input type="time" class="time-picker end-time" value="18:00"></div></div></td>
                  <td style="text-align:right;padding-right:10px;"><span class="duration-badge off">休眠</span></td>
                  <td style="width:46px;text-align:right;"><button class="switch" aria-label="週日"><span></span></button></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Quick settings / Status Sidebar -->
        <div class="panel quick-settings">
          <div class="panel-heading">
            <div><span class="section-eyebrow">SCHEDULER STATUS</span><h3>排程守候狀態</h3></div>
            <span class="settings-symbol">✦</span>
          </div>
          <div class="setting-row">
            <div><strong>目前狀態</strong><span id="schedStatusText">檢查中...</span></div>
          </div>
          <div class="setting-row">
            <div><strong>下次自動開啟</strong><span id="schedNextRunText">計算中...</span></div>
          </div>
          <div class="setting-row">
            <div><strong>自動開啟機制</strong><span>只要電腦與本服務處於開機運作狀態，到了排程時間就會自動點名。</span></div>
          </div>
          <div class="setting-row">
            <div><strong>省電休眠</strong><span>超出排程時間會自動進入休眠暫停輪詢，不浪費電腦效能與網路流量。</span></div>
          </div>
        </div>
      </div>
    </section>

    <!-- ═══════ Settings View ═══════ -->
    <section class="view" id="settings-view">
      <div class="page-heading compact">
        <div>
          <p class="eyebrow">個人化設定</p>
          <h1>帳號與設定</h1>
          <p class="heading-copy">管理你的 iClass 帳號。</p>
        </div>
        <span class="saved-label" id="savedLabel" style="display:none;"><span></span> 已同步</span>
      </div>

      <div class="settings-layout">
        <!-- Account Panel -->
        <div class="panel account-panel">
          <div class="panel-heading">
            <div><span class="section-eyebrow">ACCOUNT</span><h3>帳號資訊</h3></div>
            <span class="connected-label" id="connectedLabel"><span></span> 已設定</span>
          </div>
          <div class="profile-banner">
            <div class="large-avatar" id="profileAvatar">--</div>
            <div>
              <strong id="profileSchoolName">--</strong>
              <span id="profileUserId">未設定帳號</span>
              <small id="profileDesc">請填寫下方表單並儲存</small>
            </div>
          </div>
          <div class="form-grid">
            <label>
              <span>學校</span>
              <div class="form-field">
                <select id="schoolSelect">
                  <option value="tku">淡江大學（TKU）</option>
                  <option value="thu">東海大學（THU）</option>
                  <option value="tronclass">TronClass 公有雲</option>
                </select>
              </div>
            </label>
            <label>
              <span>帳號（學號）</span>
              <div class="form-field">
                <input type="text" id="userVal" placeholder="請輸入學號">
              </div>
            </label>
            <label style="grid-column:span 2;">
              <span>密碼</span>
              <div class="form-field">
                <input type="password" id="passwdVal" placeholder="請輸入密碼" style="flex:1;">
                <button class="show-pw-btn" id="togglePass">顯示</button>
              </div>
            </label>
          </div>
          <button class="primary-button full" id="saveConfigBtn">儲存帳號設定</button>
          <button class="primary-button full" id="saveAndStartBtn" style="margin-top:8px;background:linear-gradient(135deg,#27d39b,#139a6e);color:#08131d;border:none;">儲存並立即啟動監控</button>
          <div style="font-size:10px;color:var(--muted);margin-top:10px;line-height:1.4;">
            💡 提示：設定將安全保存在本機瀏覽器與本次連線中，不會上傳至公開伺服器。
          </div>
        </div>



        <!-- Danger Panel -->
        <div class="panel danger-panel">
          <div>
            <strong>清除 Session</strong>
            <span>清除本次 Web GUI Session 的暫存資料，不影響設定檔。</span>
          </div>
          <button class="danger-button" id="clearSessionBtn">清除</button>
        </div>
      </div>
    </section>

    <!-- Bottom Nav (mobile) -->
    <nav class="bottom-nav" aria-label="行動版導覽">
      <button class="nav-item active" data-view="dashboard"><span class="nav-icon">⌂</span><span>控制台</span></button>
      <button class="nav-item" data-view="schedule"><span class="nav-icon">◷</span><span>排程</span></button>
      <button class="nav-item" data-view="settings"><span class="nav-icon">⚙</span><span>設定</span></button>
    </nav>
  </main>
</div>

<!-- Toast -->
<div class="toast" id="toast">
  <span>✓</span>
  <div><strong id="toastTitle">已更新</strong><br><small id="toastDetail"></small></div>
</div>

<script>
// ── Global State ──
var isRunning = false;
var isFetchingLogs = false;
var selectedMinutes = 0;
var timerEndAt = null;
var timerInterval = null;

// ── View switching ──
const VIEWS = { dashboard:'控制台', schedule:'上課排程', settings:'帳號設定' };
const allNavItems = document.querySelectorAll('[data-view]');
const viewSections = document.querySelectorAll('.view');

function switchView(name) {
  if (!VIEWS[name]) return;
  viewSections.forEach(s => s.classList.toggle('active', s.id === name + '-view'));
  allNavItems.forEach(b => b.classList.toggle('active', b.dataset.view === name));
  document.getElementById('breadcrumb-title').textContent = VIEWS[name];
  if (window.location.hash !== '#' + name) {
    history.replaceState(null, '', '#' + name);
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function handleHash() {
  const h = (window.location.hash || '').replace('#', '').trim();
  if (VIEWS[h]) switchView(h);
}
window.addEventListener('hashchange', handleHash);

allNavItems.forEach(b => b.addEventListener('click', () => switchView(b.dataset.view)));

// ── Toast ──
let toastTimer;
function showToast(title, detail = '', type = 'ok') {
  const t = document.getElementById('toast');
  const span = t.querySelector('span');
  if (type === 'err') {
    span.textContent = '✗';
    span.style.color = '#ff687c';
    t.style.borderColor = 'rgba(255,104,124,.35)';
    t.style.background  = '#2a1515';
  } else if (type === 'warn') {
    span.textContent = '⚠️';
    span.style.color = '#ffb340';
    t.style.borderColor = 'rgba(255,179,64,.35)';
    t.style.background  = '#261f14';
  } else {
    span.textContent = '✓';
    span.style.color = 'var(--mint)';
    t.style.borderColor = 'rgba(39,211,155,.28)';
    t.style.background  = '#152a2a';
  }
  document.getElementById('toastTitle').textContent = title;
  document.getElementById('toastDetail').textContent = detail;
  t.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), 3500);
}

const goSetBtn = document.getElementById('goSettingsBtn');
if (goSetBtn) {
  goSetBtn.addEventListener('click', () => {
    switchView('settings');
    setTimeout(() => {
      const u = document.getElementById('userVal');
      if (u) { u.focus(); u.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
    }, 200);
  });
}

// ── Time update ──
function updateTime() {
  const now = new Date();
  document.getElementById('live-time').textContent =
    now.toLocaleTimeString('zh-TW', { hour:'2-digit', minute:'2-digit', hour12:false });
  const days = ['日','一','二','三','四','五','六'];
  document.getElementById('todayLabel').textContent =
    `星期${days[now.getDay()]}，${now.getMonth()+1} 月 ${now.getDate()} 日`;
}
updateTime();
setInterval(updateTime, 30000);

// ── Password toggle ──
document.getElementById('togglePass').addEventListener('click', () => {
  const p = document.getElementById('passwdVal');
  const b = document.getElementById('togglePass');
  if (p.type === 'password') { p.type = 'text'; b.textContent = '隱藏'; }
  else                        { p.type = 'password'; b.textContent = '顯示'; }
});

// ── Schedule Helpers & Durations ──
function calcDuration(startTime, endTime) {
  if (!startTime || !endTime) return '--';
  const [sh, sm] = startTime.split(':').map(Number);
  const [eh, em] = endTime.split(':').map(Number);
  if (isNaN(sh) || isNaN(sm) || isNaN(eh) || isNaN(em)) return '--';
  let diffMin = (eh * 60 + em) - (sh * 60 + sm);
  if (diffMin < 0) diffMin += 1440;
  if (diffMin === 0) return '全天 24h';
  const h = Math.floor(diffMin / 60);
  const m = diffMin % 60;
  return m > 0 ? `${h}h ${m}m` : `${h} 小時`;
}

function updateRowDuration(row) {
  const sw = row.querySelector('.switch');
  const badge = row.querySelector('.duration-badge');
  const sInput = row.querySelector('.start-time');
  const eInput = row.querySelector('.end-time');
  const enabled = sw && sw.classList.contains('on');

  if (!enabled) {
    row.classList.add('disabled');
    if (badge) { badge.className = 'duration-badge off'; badge.textContent = '休眠'; }
  } else {
    row.classList.remove('disabled');
    if (badge && sInput && eInput) {
      badge.className = 'duration-badge';
      badge.textContent = calcDuration(sInput.value, eInput.value);
    }
  }
}

// ── Schedule switch toggles ──
document.querySelectorAll('#scheduleTableBody .switch').forEach(sw => {
  sw.addEventListener('click', () => {
    sw.classList.toggle('on');
    const row = sw.closest('tr');
    if (row) updateRowDuration(row);
    updateScheduleSummary();
  });
});

// ── Schedule time inputs change ──
document.querySelectorAll('#scheduleTableBody .time-picker').forEach(inp => {
  inp.addEventListener('change', () => {
    const row = inp.closest('tr');
    if (row) updateRowDuration(row);
    updateScheduleSummary();
  });
});

// ── Preset chips handler ──
document.querySelectorAll('.preset-chip').forEach(chip => {
  chip.addEventListener('click', () => {
    const p = chip.dataset.preset;
    const rows = document.querySelectorAll('#scheduleTableBody tr[data-day]');
    if (p === 'weekday_full') {
      rows.forEach(r => {
        const d = parseInt(r.dataset.day);
        if (d < 5) {
          r.querySelector('.start-time').value = '08:00';
          r.querySelector('.end-time').value   = '18:00';
          r.querySelector('.switch').classList.add('on');
        }
      });
    } else if (p === 'morning') {
      rows.forEach(r => {
        if (r.querySelector('.switch.on')) {
          r.querySelector('.start-time').value = '08:00';
          r.querySelector('.end-time').value   = '12:00';
        }
      });
    } else if (p === 'afternoon') {
      rows.forEach(r => {
        if (r.querySelector('.switch.on')) {
          r.querySelector('.start-time').value = '13:00';
          r.querySelector('.end-time').value   = '18:00';
        }
      });
    } else if (p === 'night') {
      rows.forEach(r => {
        if (r.querySelector('.switch.on')) {
          r.querySelector('.start-time').value = '18:00';
          r.querySelector('.end-time').value   = '22:00';
        }
      });
    } else if (p === 'all_day') {
      rows.forEach(r => {
        if (r.querySelector('.switch.on')) {
          r.querySelector('.start-time').value = '08:00';
          r.querySelector('.end-time').value   = '22:00';
        }
      });
    } else if (p === 'weekdays_only') {
      rows.forEach(r => {
        const d = parseInt(r.dataset.day);
        r.querySelector('.switch').classList.toggle('on', d < 5);
      });
    } else if (p === 'all_on') {
      rows.forEach(r => r.querySelector('.switch').classList.add('on'));
    }
    rows.forEach(r => updateRowDuration(r));
    updateScheduleSummary();
    showToast('已套用時段範本', '請記得點擊「儲存排程」儲存變更');
  });
});

// ── Auto schedule master switch ──
const autoSchedSwitch = document.getElementById('autoScheduleSwitch');
if (autoSchedSwitch) {
  autoSchedSwitch.addEventListener('click', async () => {
    autoSchedSwitch.classList.toggle('on');
    const enabled = autoSchedSwitch.classList.contains('on');
    const badge = document.getElementById('autoScheduleBadge');
    if (badge) {
      badge.className = enabled ? 'auto-badge on' : 'auto-badge off';
      badge.textContent = enabled ? '● 守候中' : '○ 已暫停';
    }
    try {
      await fetch('/api/schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ auto_schedule_enabled: enabled })
      });
      showToast(enabled ? '已開啟排程自動監控' : '已關閉排程自動監控', '');
    } catch(e) {}
    updateScheduleSummary();
  });
}

function updateScheduleSummary() {
  const rows = document.querySelectorAll('#scheduleTableBody tr[data-day]');
  let enabled = 0;
  rows.forEach(r => { if (r.querySelector('.switch.on')) enabled++; });
  const countEl = document.getElementById('schedEnabledDays');
  if (countEl) countEl.innerHTML = `${enabled} <small>天</small>`;
  const pct = Math.round((enabled / 7) * 100);
  const covEl = document.getElementById('schedCoverage');
  if (covEl) covEl.textContent = pct + '%';
  const barEl = document.getElementById('schedProgressBar');
  if (barEl) barEl.style.width = pct + '%';

  // Today slot & Next run
  const now = new Date();
  const dayIdx = now.getDay(); // 0=Sun..6=Sat
  const tableDay = dayIdx === 0 ? 6 : dayIdx - 1;
  const todayRow = document.querySelector(`#scheduleTableBody tr[data-day="${tableDay}"]`);
  const slotEl = document.getElementById('schedTodaySlot');
  const statusEl = document.getElementById('schedStatusText');
  const nextRunEl = document.getElementById('schedNextRunText');

  const autoOn = document.getElementById('autoScheduleSwitch') && document.getElementById('autoScheduleSwitch').classList.contains('on');

  if (todayRow && slotEl) {
    const isTodayOn = todayRow.querySelector('.switch.on');
    const sVal = (todayRow.querySelector('.start-time') || {}).value || '08:00';
    const eVal = (todayRow.querySelector('.end-time') || {}).value || '18:00';
    if (isTodayOn) {
      slotEl.textContent = `${sVal}–${eVal}`;
    } else {
      slotEl.textContent = '本日休眠';
    }
  }

  if (statusEl) {
    if (!autoOn) {
      statusEl.textContent = '排程自動監控已關閉';
    } else if (isRunning) {
      statusEl.textContent = '監控執行中 (自動點名)';
    } else {
      statusEl.textContent = '背景守候中 (時間抵達自動開啟)';
    }
  }

  if (nextRunEl) {
    const dayNames = ['週日','週一','週二','週三','週四','週五','週六'];
    let foundNext = null;
    for (let i = 0; i < 7; i++) {
      const d = (dayIdx + i) % 7;
      const tDay = d === 0 ? 6 : d - 1;
      const r = document.querySelector(`#scheduleTableBody tr[data-day="${tDay}"]`);
      if (r && r.querySelector('.switch.on')) {
        const sVal = (r.querySelector('.start-time') || {}).value || '08:00';
        const label = i === 0 ? '今天' : (i === 1 ? '明天' : dayNames[d]);
        foundNext = `${label} ${sVal}`;
        break;
      }
    }
    nextRunEl.textContent = foundNext || '尚未啟用任何排程';
  }
}

updateScheduleSummary();

// ── Fetch Config ──
async function fetchConfig() {
  try {
    const res  = await fetch('/api/config');
    const data = await res.json();
    if (!data.ok) return;

    let user   = data.config.user || '';
    let passwd = data.config.passwd || '';
    let school = data.config.school || 'tku';

    // If server has no credentials, attempt restoring from localStorage
    if (!user || user === 'YOUR_STUDENT_ID') {
      const localUser   = localStorage.getItem('auto_rollcall_user');
      const localPasswd = localStorage.getItem('auto_rollcall_passwd');
      const localSchool = localStorage.getItem('auto_rollcall_school');
      if (localUser && localPasswd) {
        user = localUser;
        passwd = localPasswd;
        if (localSchool) school = localSchool;
        fetch('/api/config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user, passwd, school })
        }).catch(() => {});
      }
    }

    document.getElementById('userVal').value      = (user && user !== 'YOUR_STUDENT_ID') ? user : '';
    document.getElementById('passwdVal').value    = (passwd && passwd !== 'YOUR_PASSWORD') ? passwd : '';
    document.getElementById('schoolSelect').value = school;

    updateProfileBanner(user, school);

    if (data.config.auto_schedule_enabled !== undefined) {
      const sw = document.getElementById('autoScheduleSwitch');
      if (sw) sw.classList.toggle('on', !!data.config.auto_schedule_enabled);
      const badge = document.getElementById('autoScheduleBadge');
      if (badge) {
        badge.className = data.config.auto_schedule_enabled ? 'auto-badge on' : 'auto-badge off';
        badge.textContent = data.config.auto_schedule_enabled ? '● 守候中' : '○ 已暫停';
      }
    }

    const operating = data.config.operating || {};
    const rows = document.querySelectorAll('#scheduleTableBody tr[data-day]');
    rows.forEach(row => {
      const day = parseInt(row.dataset.day);
      if (operating[day] !== undefined) {
        const sInput = row.querySelector('.start-time');
        const eInput = row.querySelector('.end-time');
        const sw     = row.querySelector('.switch');
        const enabled = operating[day].enable;
        if (sw) sw.classList.toggle('on', enabled);

        if (sInput && operating[day].start) sInput.value = operating[day].start;
        if (eInput && operating[day].end)   eInput.value = operating[day].end;

        updateRowDuration(row);
      }
    });
    updateScheduleSummary();
  } catch(e) { console.error('fetchConfig', e); }
}

function updateProfileBanner(user, school) {
  const isReal = !!(user && user !== 'YOUR_STUDENT_ID');
  const schoolMap = { tku:'淡江大學', thu:'東海大學', tronclass:'TronClass' };
  const schoolName = schoolMap[school] || school || '--';
  const initials = isReal ? (school ? school.substring(0,2).toUpperCase() : 'TK') : '--';

  document.getElementById('profileAvatar').textContent  = initials;
  document.getElementById('sidebarAvatar').textContent  = initials;
  document.getElementById('profileSchoolName').textContent = schoolName;
  document.getElementById('sidebarSchool').textContent  = schoolName;
  document.getElementById('profileUserId').textContent  = isReal ? user : '未設定帳號';
  document.getElementById('sidebarUser').textContent    = isReal ? user : '未設定';
  document.getElementById('profileDesc').textContent    = isReal ? `${schoolName} iClass 帳號` : '請填寫下方表單並儲存';

  const online = document.getElementById('sidebarOnline');
  if (online) online.style.background = isReal ? 'var(--mint)' : 'var(--subtle)';

  const setupAlert = document.getElementById('setupAlert');
  if (setupAlert) setupAlert.style.display = isReal ? 'none' : 'flex';

  const connected = document.getElementById('connectedLabel');
  if (connected) connected.style.display = isReal ? 'flex' : 'none';
}

// ── Fetch Status ──
async function fetchStatus() {
  try {
    const res  = await fetch('/api/status');
    const data = await res.json();
    if (!data.ok) return;

    isRunning = data.running;
    const count = data.status.check_count || 0;
    document.getElementById('checkCount').textContent  = count;
    document.getElementById('statChecks').innerHTML    = `${count}<span> 次</span>`;

    let phaseLabel = '休眠中';
    if      (data.status.phase === 'monitoring') phaseLabel = '監控點名中';
    else if (data.status.phase === 'logging_in') phaseLabel = '登入中';
    else if (data.status.phase === 'standby')    phaseLabel = '休眠時段';

    const detail = data.status.detail || '';
    document.getElementById('phaseText').textContent  = phaseLabel;
    document.getElementById('statPhase').textContent  = phaseLabel;
    document.getElementById('statDetail').textContent = detail || (isRunning ? '執行中' : '尚未啟動');

    if (isRunning) {
      document.getElementById('statusPill').className   = 'status-pill';
      document.getElementById('monitorStatusText').textContent = '監控執行中';
      document.getElementById('toggleBtn').className   = 'primary-button monitor-toggle paused';
      document.getElementById('toggleLabel').textContent = '停止監控';
      document.getElementById('monitorTitle').textContent = '系統正在自動監控點名';
      document.getElementById('monitorDesc').textContent  = '排程會在上課前自動檢查簽到條件。';
      document.getElementById('statStatus').textContent   = '執行中';
      document.getElementById('dashSubtitle').textContent = '監控中，系統將自動偵測並完成點名。';
      document.querySelectorAll('.timer-opt').forEach(b => b.disabled = true);
      const cInput = document.getElementById('customTimerInput');
      if (cInput) cInput.disabled = true;
      if (data.auto_stop_at && !timerInterval) {
        startCountdown(0, data.auto_stop_at);
      }
    } else {
      document.getElementById('statusPill').className   = 'status-pill off';
      document.getElementById('monitorStatusText').textContent = '已停止';
      document.getElementById('toggleBtn').className   = 'primary-button monitor-toggle';
      document.getElementById('toggleLabel').textContent = '啟動監控';
      document.getElementById('monitorTitle').textContent = '監控尚未啟動';
      document.getElementById('monitorDesc').textContent  = '請設定帳號後按下啟動按鈕，開始自動簽到監控。';
      document.getElementById('statStatus').textContent   = '停止中';
      document.getElementById('dashSubtitle').textContent = '目前未啟動，點擊「啟動監控」開始。';
      document.querySelectorAll('.timer-opt').forEach(b => b.disabled = false);
      const cInput = document.getElementById('customTimerInput');
      if (cInput) cInput.disabled = false;
      if (timerInterval) {
        stopCountdown();
      }
    }

    renderLogs(data.logs);
    renderUpcoming();
    updateScheduleSummary();
  } catch(e) { console.error('fetchStatus', e); }
}

function renderLogs(logs) {
  const box = document.getElementById('consoleBox');
  if (!logs || logs.length === 0) {
    box.innerHTML = '<span style="color:var(--subtle);">尚無執行紀錄</span>';
    return;
  }
  const filter = document.getElementById('logFilter').value.toLowerCase().trim();
  const atBottom = box.scrollHeight - box.clientHeight <= box.scrollTop + 40;

  const items = [];
  logs.forEach(log => {
    if (filter && !log.toLowerCase().includes(filter)) return;
    let color = '#7bafd4';
    if (log.includes('成功') || log.includes('完成') || log.includes('簽到')) color = 'var(--mint)';
    else if (log.includes('警告') || log.includes('重試') || log.includes('等待')) color = 'var(--amber)';
    else if (log.includes('錯誤') || log.includes('失敗') || log.includes('異常')) color = 'var(--red)';
    items.push(`<div style="color:${color};padding-bottom:2px;">${escHtml(log)}</div>`);
  });
  box.innerHTML = items.join('') || '<span style="color:var(--subtle);">無相符紀錄</span>';
  if (atBottom || !isFetchingLogs) { box.scrollTop = box.scrollHeight; isFetchingLogs = true; }
}

function renderUpcoming() {
  // Build upcoming from schedule rows
  const ul = document.getElementById('upcomingList');
  const dayNames = ['週日','週一','週二','週三','週四','週五','週六'];
  const today = new Date().getDay(); // 0=Sun
  const items = [];
  for (let i = 0; i < 7; i++) {
    const dayIdx = (today + i) % 7;
    // data-day: Mon=0..Sun=6
    const tableDay = dayIdx === 0 ? 6 : dayIdx - 1;
    const row = document.querySelector(`#scheduleTableBody tr[data-day="${tableDay}"]`);
    if (!row) continue;
    if (!row.querySelector('.switch.on')) continue;
    const sInput = row.querySelector('.start-time');
    const eInput = row.querySelector('.end-time');
    const timeVal = (sInput && eInput) ? `${sInput.value} ~ ${eInput.value}` : '08:00 ~ 18:00';
    const label = i === 0 ? '今天' : dayNames[dayIdx];
    const now = new Date();
    const d = new Date(now); d.setDate(now.getDate() + i);
    items.push(`
      <div class="upcoming-item${i === 0 ? ' current' : ''}">
        <div class="day-box"><span>${label}</span><strong>${d.getDate()}</strong></div>
        <div class="upcoming-info"><strong>${timeVal}</strong><span>自動監控時段</span></div>
      </div>`);
    if (items.length >= 4) break;
  }
  ul.innerHTML = items.join('') || '<div style="font-size:10px;color:var(--subtle);padding:8px 0;">尚未設定啟用的排程</div>';
}

function escHtml(t) {
  return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
          .replace(/"/g,'&quot;').replace(/'/g,'&#039;');
}

// ── Save Config ──
async function performSaveConfig(silent = false) {
  const user   = document.getElementById('userVal').value.trim();
  const passwd = document.getElementById('passwdVal').value.trim();
  const school = document.getElementById('schoolSelect').value;
  if (!user || !passwd) { showToast('帳號與密碼不能為空', '', 'err'); return false; }
  try {
    const res  = await fetch('/api/config', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({user,passwd,school}) });
    const data = await res.json();
    if (data.ok) {
      localStorage.setItem('auto_rollcall_user', user);
      localStorage.setItem('auto_rollcall_passwd', passwd);
      localStorage.setItem('auto_rollcall_school', school);
      updateProfileBanner(user, school);
      document.getElementById('savedLabel').style.display = 'flex';
      if (!silent) showToast('帳號設定已儲存', '設定已同步至本次 Session');
      return true;
    } else {
      showToast('儲存失敗', data.error || '', 'err');
      return false;
    }
  } catch(e) {
    showToast('網路連線錯誤', '', 'err');
    return false;
  }
}

document.getElementById('saveConfigBtn').addEventListener('click', () => performSaveConfig(false));

const saveAndStart = document.getElementById('saveAndStartBtn');
if (saveAndStart) {
  saveAndStart.addEventListener('click', async () => {
    const ok = await performSaveConfig(true);
    if (!ok) return;
    showToast('帳號已設定完成', '正在為您切換至控制台並啟動監控...');
    switchView('dashboard');
    if (!isRunning) {
      setTimeout(() => {
        const tb = document.getElementById('toggleBtn');
        if (tb) tb.click();
      }, 350);
    }
  });
}

// ── Save Schedule ──
document.getElementById('saveScheduleBtn').addEventListener('click', async () => {
  const operating = {};
  document.querySelectorAll('#scheduleTableBody tr[data-day]').forEach(row => {
    const day = parseInt(row.dataset.day);
    const sVal = (row.querySelector('.start-time') || {}).value || '08:00';
    const eVal = (row.querySelector('.end-time') || {}).value || '18:00';
    operating[day] = {
      enable: !!row.querySelector('.switch.on'),
      start:  sVal,
      end:    eVal,
      range:  `${sVal} - ${eVal}`
    };
  });
  const autoSw = document.getElementById('autoScheduleSwitch');
  const auto_schedule_enabled = autoSw ? autoSw.classList.contains('on') : true;

  try {
    const res  = await fetch('/api/schedule', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({ operating, auto_schedule_enabled })
    });
    const data = await res.json();
    if (data.ok) {
      showToast('排程設定已儲存', '系統將依此時間表自動守候與監控');
      updateScheduleSummary();
    } else {
      showToast('儲存失敗', data.error||'','err');
    }
  } catch(e) { showToast('網路連線錯誤','','err'); }
});

// ── Timer selector & Auto-stop ──
const timerBtns = document.querySelectorAll('.timer-opt');
const customBtn = document.getElementById('customTimerBtn');
const customWrap = document.getElementById('customTimerWrap');
const customInput = document.getElementById('customTimerInput');

timerBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    if (isRunning) return;
    const min = parseInt(btn.dataset.min);
    if (min === -1) {
      if (customWrap) customWrap.style.display = 'inline-flex';
      if (customInput) customInput.focus();
      timerBtns.forEach(b => b.classList.remove('active'));
      if (customBtn) customBtn.classList.add('active');
      const customVal = customInput ? parseInt(customInput.value) : 0;
      selectedMinutes = (!isNaN(customVal) && customVal > 0) ? customVal : 0;
    } else {
      if (customWrap) customWrap.style.display = 'none';
      timerBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      selectedMinutes = min;
    }
  });
});

if (customInput) {
  customInput.addEventListener('input', () => {
    if (isRunning) return;
    const v = parseInt(customInput.value);
    selectedMinutes = (!isNaN(v) && v > 0) ? v : 0;
  });
}

function startCountdown(minutes, targetEpoch = null) {
  clearInterval(timerInterval);
  if (targetEpoch) {
    timerEndAt = new Date(targetEpoch * 1000);
  } else if (minutes > 0) {
    timerEndAt = new Date(Date.now() + minutes * 60 * 1000);
  } else {
    stopCountdown();
    return;
  }
  const badge = document.getElementById('countdownBadge');
  if (badge) badge.style.display = 'inline-flex';
  updateCountdownDisplay();
  timerInterval = setInterval(async () => {
    const remaining = timerEndAt - Date.now();
    if (remaining <= 0) {
      stopCountdown();
      if (isRunning) {
        try {
          const res  = await fetch('/api/stop', { method:'POST' });
          const data = await res.json();
          if (data.ok) {
            isRunning = false;
            showToast('定時停止', '設定時間已到，監控服務已自動關閉');
            fetchStatus();
          }
        } catch(e) {}
      }
    } else {
      updateCountdownDisplay();
    }
  }, 1000);
}

function stopCountdown() {
  clearInterval(timerInterval);
  timerInterval = null;
  timerEndAt    = null;
  const badge = document.getElementById('countdownBadge');
  if (badge) badge.style.display = 'none';
}

function updateCountdownDisplay() {
  if (!timerEndAt) return;
  const remaining = Math.max(0, timerEndAt - Date.now());
  const totalSec  = Math.ceil(remaining / 1000);
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  const label = h > 0
    ? `剩餘 ${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`
    : `剩餘 ${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
  const txt = document.getElementById('countdownText');
  if (txt) txt.textContent = label;
}

// ── Toggle Monitor ──
document.getElementById('toggleBtn').addEventListener('click', async () => {
  const btn = document.getElementById('toggleBtn');

  if (!isRunning) {
    const user   = document.getElementById('userVal').value.trim();
    const passwd = document.getElementById('passwdVal').value.trim();
    const school = document.getElementById('schoolSelect').value;
    const isRealUser   = !!(user && user !== 'YOUR_STUDENT_ID');
    const isRealPasswd = !!(passwd && passwd !== 'YOUR_PASSWORD');

    if (!isRealUser || !isRealPasswd) {
      showToast('尚未填寫學號與密碼', '正在為您切換至帳號設定頁面...', 'warn');
      switchView('settings');
      setTimeout(() => {
        const u = document.getElementById('userVal');
        if (u) { u.focus(); u.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
      }, 250);
      return;
    }

    try {
      const cr = await fetch('/api/config', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({user,passwd,school}) });
      if (!(await cr.json()).ok) { showToast('帳號自動儲存失敗', '', 'err'); return; }

      const operating = {};
      document.querySelectorAll('#scheduleTableBody tr[data-day]').forEach(row => {
        const day = parseInt(row.dataset.day);
        const sVal = (row.querySelector('.start-time') || {}).value || '08:00';
        const eVal = (row.querySelector('.end-time') || {}).value || '18:00';
        operating[day] = {
          enable: !!row.querySelector('.switch.on'),
          start: sVal,
          end: eVal,
          range: `${sVal} - ${eVal}`
        };
      });
      const sr = await fetch('/api/schedule', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({operating}) });
      if (!(await sr.json()).ok) { showToast('排程自動儲存失敗','','err'); return; }
    } catch(e) { showToast('自動儲存失敗','','err'); return; }
  }

  btn.disabled = true;
  try {
    const url  = isRunning ? '/api/stop' : '/api/start';
    const bodyPayload = isRunning ? {} : { auto_stop_minutes: selectedMinutes };
    const res  = await fetch(url, {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify(bodyPayload)
    });
    const data = await res.json();
    if (data.ok) {
      isRunning = !isRunning;
      if (isRunning) {
        const detail = selectedMinutes ? `${selectedMinutes >= 60 ? (selectedMinutes/60) + ' 小時' : selectedMinutes + ' 分鐘'}後自動停止` : '';
        showToast('監控服務已啟動', detail);
        startCountdown(selectedMinutes);
        document.querySelectorAll('.timer-opt').forEach(b => b.disabled = true);
        if (customInput) customInput.disabled = true;
      } else {
        showToast('監控服務已停止', '');
        stopCountdown();
        document.querySelectorAll('.timer-opt').forEach(b => b.disabled = false);
        if (customInput) customInput.disabled = false;
      }
      fetchStatus();
    } else {
      showToast('操作失敗', data.error || '', 'err');
      if (data.error && data.error.includes('學號與密碼')) {
        switchView('settings');
        setTimeout(() => {
          const u = document.getElementById('userVal');
          if (u) { u.focus(); u.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
        }, 250);
      }
    }
  } catch(e) { showToast('連線異常','','err'); }
  finally { btn.disabled = false; }
});

// ── Clear session ──
document.getElementById('clearSessionBtn').addEventListener('click', () => {
  localStorage.removeItem('auto_rollcall_user');
  localStorage.removeItem('auto_rollcall_passwd');
  localStorage.removeItem('auto_rollcall_school');
  document.getElementById('userVal').value = '';
  document.getElementById('passwdVal').value = '';
  updateProfileBanner('', 'tku');
  showToast('Session 與本機快取已清除', '請重新設定帳號');
});

// ── Log filter ──
document.getElementById('logFilter').addEventListener('input', () => fetchStatus());

// ── Init ──
handleHash();
fetchConfig();
fetchStatus();
setInterval(fetchStatus, 1500);
</script>
</body>
</html>
"""



# Session-isolation variables and proxies

CURRENT_SESSION_ID = contextvars.ContextVar('current_session_id', default=None)
USER_SESSIONS = {}

class UserSessionState:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.last_accessed_at = time.time()
        
        cfg = copy.deepcopy(ctx.DEFAULT_CONFIG)
        # Clear out credentials in profiles and account
        profiles = cfg.setdefault('accounts', {}).setdefault('profiles', {})
        for prof in profiles.values():
            prof['user'] = 'YOUR_STUDENT_ID'
            prof['passwd'] = 'YOUR_PASSWORD'
        if 'account' in cfg:
            cfg['account']['user'] = 'YOUR_STUDENT_ID'
            cfg['account']['passwd'] = 'YOUR_PASSWORD'
            
        self.CONFIG = cfg
        self.MONITOR_STATUS = {
            "phase": "standby",
            "check_count": 0,
            "detail": "",
            "rollcall_status": "",
            "next_switch_at": None,
            "teacher_state": "off",
        }
        self.LAST_LOGIN_RESULT = ctx.LoginResult(status="missing_credentials", credential_source="missing")
        self.TEACHER_LOGIN_RESULT = ctx.LoginResult(status="missing_credentials", credential_source="missing")
        self.LAST_ROLLCALL_PROGRESS = {}
        self.COMPLETED_NUMBER_ROLLCALLS = {}
        self.COMPLETED_RADAR_ROLLCALLS = {}
        self.COMPLETED_QR_ROLLCALLS = {}
        self.QR_ASSIST_ATTEMPTS = {}
        self.ACTIVE_TEACHER_QR_ASSISTS = {}
        self.TEACHER_SESSION = None
        self.TEACHER_ENDPOINTS = None
        self.TEACHER_READY = False
        self.TEACHER_COURSE_ID = ""
        self.GUI_LOGS = []
        self.IS_LOGGING_IN = False
        self.NOTIFICATION_SINKS = []
        self.CONFIG_BOOTSTRAPPED = True
        
        self.cookie_cache = {}
        self.monitor_task = None
        self.shutdown_event = None
        self.auto_stop_at = None
        self.timer_task = None
        self.auto_schedule_enabled = True
        self.manual_stopped_at = 0.0

def get_session_state(session_id: str) -> UserSessionState:
    if session_id not in USER_SESSIONS:
        USER_SESSIONS[session_id] = UserSessionState(session_id)
    state = USER_SESSIONS[session_id]
    state.last_accessed_at = time.time()
    return state

# Session proxies for direct module dictionary accesses
class SessionProxyDict(dict):
    def __init__(self, name, default_val):
        self._name = name
        self._default_val = default_val

    def _get_target(self):
        session_id = CURRENT_SESSION_ID.get()
        if session_id is not None:
            return getattr(get_session_state(session_id), self._name)
        return self._default_val

    def __getitem__(self, key):
        return self._get_target()[key]

    def __setitem__(self, key, value):
        self._get_target()[key] = value

    def __delitem__(self, key):
        del self._get_target()[key]

    def __contains__(self, key):
        return key in self._get_target()

    def __len__(self):
        return len(self._get_target())

    def __iter__(self):
        return iter(self._get_target())

    def keys(self):
        return self._get_target().keys()

    def values(self):
        return self._get_target().values()

    def items(self):
        return self._get_target().items()

    def get(self, key, default=None):
        return self._get_target().get(key, default)

    def update(self, *args, **kwargs):
        self._get_target().update(*args, **kwargs)

    def clear(self):
        self._get_target().clear()

    def setdefault(self, key, default=None):
        return self._get_target().setdefault(key, default)

    def pop(self, key, default=None):
        return self._get_target().pop(key, default)

    def popitem(self):
        return self._get_target().popitem()

    def copy(self):
        return self._get_target().copy()

    def __repr__(self):
        return repr(self._get_target())

    def __str__(self):
        return str(self._get_target())

class SessionProxyList(list):
    def __init__(self, name, default_val):
        self._name = name
        self._default_val = default_val

    def _get_target(self):
        session_id = CURRENT_SESSION_ID.get()
        if session_id is not None:
            return getattr(get_session_state(session_id), self._name)
        return self._default_val

    def append(self, item):
        self._get_target().append(item)

    def pop(self, index=-1):
        return self._get_target().pop(index)

    def extend(self, iterable):
        self._get_target().extend(iterable)

    def clear(self):
        self._get_target().clear()

    def __len__(self):
        return len(self._get_target())

    def __iter__(self):
        return iter(self._get_target())

    def __getitem__(self, index):
        return self._get_target()[index]

    def __setitem__(self, index, value):
        self._get_target()[index] = value

    def __delitem__(self, index):
        del self._get_target()[index]

    def __repr__(self):
        return repr(self._get_target())

    def __str__(self):
        return str(self._get_target())


SESSION_ISOLATED_VARS = {
    "CONFIG",
    "MONITOR_STATUS",
    "LAST_LOGIN_RESULT",
    "LAST_ROLLCALL_PROGRESS",
    "COMPLETED_NUMBER_ROLLCALLS",
    "COMPLETED_RADAR_ROLLCALLS",
    "COMPLETED_QR_ROLLCALLS",
    "QR_ASSIST_ATTEMPTS",
    "ACTIVE_TEACHER_QR_ASSISTS",
    "TEACHER_SESSION",
    "TEACHER_ENDPOINTS",
    "TEACHER_READY",
    "TEACHER_COURSE_ID",
    "TEACHER_LOGIN_RESULT",
    "GUI_LOGS",
    "IS_LOGGING_IN",
    "NOTIFICATION_SINKS",
    "CONFIG_BOOTSTRAPPED",
}

class SessionIsolatedModule(types.ModuleType):
    def __getattribute__(self, name):
        if name in SESSION_ISOLATED_VARS:
            session_id = CURRENT_SESSION_ID.get()
            if session_id is not None:
                state = get_session_state(session_id)
                return getattr(state, name)
        return super().__getattribute__(name)

    def __setattr__(self, name, value):
        if name in SESSION_ISOLATED_VARS:
            session_id = CURRENT_SESSION_ID.get()
            if session_id is not None:
                state = get_session_state(session_id)
                setattr(state, name, value)
                return
        super().__setattr__(name, value)


# Mocks for file operations
def mock_save_config():
    return True

def mock_bootstrap_config(force=False):
    session_id = CURRENT_SESSION_ID.get()
    if session_id is not None:
        state = get_session_state(session_id)
        state.CONFIG = ctx.normalize_config(state.CONFIG)
        state.CONFIG_BOOTSTRAPPED = True
        return state.CONFIG
    return ctx.normalize_config(ctx.CONFIG)

def mock_save_session_cookies(session, base_dir, profile_name):
    session_id = CURRENT_SESSION_ID.get()
    if session_id is not None:
        state = get_session_state(session_id)
        records = []
        for cookie in getattr(session, "cookie_jar", []):
            records.append(
                {
                    "key": getattr(cookie, "key", ""),
                    "value": getattr(cookie, "value", ""),
                    "domain": cookie.get("domain", "") if hasattr(cookie, "get") else "",
                    "path": cookie.get("path", "/") if hasattr(cookie, "get") else "/",
                }
            )
        state.cookie_cache[profile_name] = records
        return True
    return False

def mock_load_session_cookies(session, base_dir, profile_name):
    session_id = CURRENT_SESSION_ID.get()
    if session_id is not None:
        state = get_session_state(session_id)
        records = state.cookie_cache.get(profile_name)
        if not records:
            return False
        for record in records:
            key = str(record.get("key", "") or "")
            value = str(record.get("value", "") or "")
            if key:
                session.cookie_jar.update_cookies({key: value})
        return True
    return False

def mock_clear_session_cookies(base_dir, profile_name):
    session_id = CURRENT_SESSION_ID.get()
    if session_id is not None:
        state = get_session_state(session_id)
        state.cookie_cache.pop(profile_name, None)
        return True
    return False

def mock_mark_monitor_state(base_dir, profile, state, heartbeat=True):
    return {}

def mock_mark_login_result(base_dir, profile, login_result):
    return {}

def mock_mark_check_result(base_dir, profile, status, rollcall_id="", rollcall_type=""):
    return {}

def mock_mark_profile_error(base_dir, profile, status, message):
    return {}

def mock_load_runtime_state(base_dir):
    from troTHU.account_runtime_store import AccountRuntimeSnapshot
    return AccountRuntimeSnapshot(store_status="missing")

def mock_log(*args, **kwargs):
    return True


def append_gui_log(msg: str):
    ctx.GUI_LOGS.append(str(msg))


def setup_session_isolation():
    # 1. Install module subclass
    ctx.__class__ = SessionIsolatedModule
    
    # 2. Setup proxies in module dict
    ctx.__dict__['CONFIG'] = SessionProxyDict('CONFIG', ctx.CONFIG)
    ctx.__dict__['MONITOR_STATUS'] = SessionProxyDict('MONITOR_STATUS', ctx.MONITOR_STATUS)
    ctx.__dict__['LAST_ROLLCALL_PROGRESS'] = SessionProxyDict('LAST_ROLLCALL_PROGRESS', ctx.LAST_ROLLCALL_PROGRESS)
    ctx.__dict__['COMPLETED_NUMBER_ROLLCALLS'] = SessionProxyDict('COMPLETED_NUMBER_ROLLCALLS', ctx.COMPLETED_NUMBER_ROLLCALLS)
    ctx.__dict__['COMPLETED_RADAR_ROLLCALLS'] = SessionProxyDict('COMPLETED_RADAR_ROLLCALLS', ctx.COMPLETED_RADAR_ROLLCALLS)
    ctx.__dict__['COMPLETED_QR_ROLLCALLS'] = SessionProxyDict('COMPLETED_QR_ROLLCALLS', ctx.COMPLETED_QR_ROLLCALLS)
    ctx.__dict__['QR_ASSIST_ATTEMPTS'] = SessionProxyDict('QR_ASSIST_ATTEMPTS', ctx.QR_ASSIST_ATTEMPTS)
    ctx.__dict__['ACTIVE_TEACHER_QR_ASSISTS'] = SessionProxyDict('ACTIVE_TEACHER_QR_ASSISTS', ctx.ACTIVE_TEACHER_QR_ASSISTS)
    ctx.__dict__['GUI_LOGS'] = SessionProxyList('GUI_LOGS', getattr(ctx, 'GUI_LOGS', []))
    ctx.__dict__['NOTIFICATION_SINKS'] = SessionProxyList('NOTIFICATION_SINKS', getattr(ctx, 'NOTIFICATION_SINKS', []))

    # 3. Register mocked functions
    ctx.save_config = mock_save_config
    ctx.bootstrap_config = mock_bootstrap_config
    ctx.save_session_cookies = mock_save_session_cookies
    ctx.load_session_cookies = mock_load_session_cookies
    ctx.clear_session_cookies = mock_clear_session_cookies
    ctx.mark_monitor_state = mock_mark_monitor_state
    ctx.mark_login_result = mock_mark_login_result
    ctx.mark_check_result = mock_mark_check_result
    ctx.mark_profile_error = mock_mark_profile_error
    ctx.load_runtime_state = mock_load_runtime_state
    ctx.log = mock_log
    ctx.append_gui_log = append_gui_log
    orig_log_print = getattr(ctx, 'log_print', None)
    def web_log_print(msg: ctx.Any) -> None:
        try:
            append_gui_log(str(msg))
        except Exception:
            pass
        if orig_log_print:
            try:
                orig_log_print(msg)
            except Exception:
                pass
    ctx.log_print = web_log_print


@web.middleware
async def session_middleware(request, handler):
    session_id = request.cookies.get("session_id")
    is_new = False
    if not session_id or session_id not in USER_SESSIONS:
        session_id = uuid.uuid4().hex
        is_new = True
    
    token = CURRENT_SESSION_ID.set(session_id)
    try:
        get_session_state(session_id)
        response = await handler(request)
        response.set_cookie("session_id", session_id, path="/", max_age=604800, httponly=True)
        return response
    finally:
        CURRENT_SESSION_ID.reset(token)


async def session_cleanup_loop():
    while True:
        try:
            await asyncio.sleep(3600)  # Check every hour
            now = time.time()
            for session_id, state in list(USER_SESSIONS.items()):
                # 7 days = 604800 seconds
                if now - state.last_accessed_at > 604800:
                    if state.monitor_task and not state.monitor_task.done():
                        state.shutdown_event.set()
                        try:
                            await state.monitor_task
                        except Exception:
                            pass
                    USER_SESSIONS.pop(session_id, None)
        except asyncio.CancelledError:
            break
        except Exception:
            pass


# aiohttp HTTP Handler functions

async def serve_index(request):
    return web.Response(text=HTML_CONTENT, content_type='text/html')

async def serve_favicon(request):
    return web.Response(status=204)

async def api_get_config(request):
    session_id = CURRENT_SESSION_ID.get()
    state = get_session_state(session_id)
    # Retrieve current active profile details
    active_profile = ctx.get_active_profile(ctx.CONFIG)
    school = ctx.CONFIG.get('provider', {}).get('current', 'tku')

    # Convert internal schedule structure (Mon..Sun -> 0..6)
    operating = {}
    for internal_day in range(7):
        schedule = ctx.CONFIG['operating'].get(internal_day, {"enable": True, "range": ["08:00", "18:00"]})
        raw_range = schedule.get("range")
        if isinstance(raw_range, (list, tuple)) and len(raw_range) >= 2:
            start_t, end_t = str(raw_range[0]), str(raw_range[1])
        elif isinstance(raw_range, str) and "-" in raw_range:
            parts = [p.strip() for p in raw_range.split("-")]
            start_t, end_t = parts[0], parts[1]
        else:
            start_t, end_t = "08:00", "18:00"

        if start_t == "00:00" and end_t == "00:00":
            start_t, end_t = "08:00", "18:00"

        operating[internal_day] = {
            "enable": bool(schedule.get("enable", True)),
            "start": start_t,
            "end": end_t,
            "range": f"{start_t} - {end_t}"
        }

    user = active_profile.user if ctx.has_real_credential(active_profile.user) else ""
    passwd = active_profile.passwd if ctx.has_real_credential(active_profile.passwd) else ""

    return web.json_response({
        "ok": True,
        "config": {
            "user": user,
            "passwd": passwd,
            "school": school,
            "auto_schedule_enabled": getattr(state, "auto_schedule_enabled", True),
            "operating": operating
        }
    })

async def api_save_config(request):
    try:
        data = await request.json()
        user = data.get("user")
        passwd = data.get("passwd")
        school = data.get("school", "tku")

        if not user or not passwd:
            return web.json_response({"ok": False, "error": "Invalid inputs"})

        # Update core configuration profile settings
        ctx.set_profile(ctx.CONFIG, 'default', user, passwd, make_current=True)
        ctx.CONFIG['provider']['current'] = school

        # Update profiles nested structure
        profiles = ctx.CONFIG.setdefault('accounts', {}).setdefault('profiles', {})
        profiles['default'] = {
            "user": user,
            "passwd": passwd,
            "label": school.upper(),
            "school": school
        }

        # Persist and reload
        ctx.save_config()
        ctx.bootstrap_config(force=True)
        return web.json_response({"ok": True})
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)})

async def api_save_schedule(request):
    try:
        session_id = CURRENT_SESSION_ID.get()
        state = get_session_state(session_id)
        data = await request.json()
        operating_data = data.get("operating", {})

        for day_str, value in operating_data.items():
            day_idx = int(day_str)
            if 0 <= day_idx <= 6:
                enable = bool(value.get("enable", True))
                start_val = str(value.get("start") or "08:00").strip()
                end_val = str(value.get("end") or "18:00").strip()
                range_str = f"{start_val} - {end_val}"
                range_pair = [start_val, end_val]

                # Update in ctx.CONFIG
                ctx.CONFIG['operating'][day_idx] = {
                    "enable": enable,
                    "range": ctx.normalize_schedule_range(range_pair, ["08:00", "18:00"]),
                    "ranges": ctx.normalize_schedule_ranges(range_pair, [["08:00", "18:00"]])
                }

        if "auto_schedule_enabled" in data:
            state.auto_schedule_enabled = bool(data["auto_schedule_enabled"])

        ctx.save_config()
        ctx.bootstrap_config(force=True)
        return web.json_response({"ok": True})
    except Exception as exc:
        return web.json_response({"ok": False, "error": str(exc)})

async def api_get_status(request):
    session_id = CURRENT_SESSION_ID.get()
    state = get_session_state(session_id)
    running = state.monitor_task is not None and not state.monitor_task.done()

    # Return status snapshot + GUI logs buffer
    return web.json_response({
        "ok": True,
        "running": running,
        "auto_stop_at": state.auto_stop_at,
        "auto_schedule_enabled": getattr(state, "auto_schedule_enabled", True),
        "status": {
            "phase": ctx.MONITOR_STATUS.get("phase", "standby"),
            "check_count": ctx.MONITOR_STATUS.get("check_count", 0),
            "detail": ctx.MONITOR_STATUS.get("detail", ""),
            "rollcall_status": ctx.MONITOR_STATUS.get("rollcall_status", "")
        },
        "logs": list(ctx.GUI_LOGS)
    })

async def api_start_monitor(request):
    session_id = CURRENT_SESSION_ID.get()
    state = get_session_state(session_id)
    if state.monitor_task is not None and not state.monitor_task.done():
        return web.json_response({"ok": False, "error": "Monitoring is already running"})

    # Ensure config has valid credentials
    active_profile = ctx.get_active_profile(ctx.CONFIG)
    if not ctx.has_real_credential(active_profile.user) or not ctx.has_real_credential(active_profile.passwd):
        return web.json_response({"ok": False, "error": "尚未設定有效的學號與密碼，請先至「帳號設定」填寫"})

    auto_stop_minutes = 0
    try:
        body = await request.json()
        auto_stop_minutes = int(body.get("auto_stop_minutes") or 0)
    except Exception:
        pass

    # Start the standard asyncio loop in the background
    state.shutdown_event = asyncio.Event()
    state.monitor_task = asyncio.create_task(ctx.app_main(input_enabled=False, external_shutdown_event=state.shutdown_event))

    if auto_stop_minutes > 0:
        state.auto_stop_at = time.time() + auto_stop_minutes * 60
        async def _timer_worker(target_epoch, mins):
            try:
                wait_sec = target_epoch - time.time()
                if wait_sec > 0:
                    await asyncio.sleep(wait_sec)
                if state.monitor_task is not None and not state.monitor_task.done():
                    ctx.append_gui_log(f"⏰ 定時時間已到（{mins} 分鐘），系統自動停止監控服務。")
                    state.shutdown_event.set()
                    try:
                        await asyncio.wait_for(state.monitor_task, timeout=5.0)
                    except Exception:
                        if state.monitor_task:
                            state.monitor_task.cancel()
                    state.monitor_task = None
                    state.shutdown_event = None
                    state.auto_stop_at = None
            except asyncio.CancelledError:
                pass
            except Exception as e:
                ctx.append_gui_log(f"定時停止計時器異常: {e}")
        state.timer_task = asyncio.create_task(_timer_worker(state.auto_stop_at, auto_stop_minutes))
        ctx.append_gui_log(f"Web GUI 已觸發監控啟動（設定 {auto_stop_minutes} 分鐘後自動停止）。")
    else:
        state.auto_stop_at = None
        ctx.append_gui_log("Web GUI 已觸發監控啟動。")

    return web.json_response({"ok": True})

async def api_stop_monitor(request):
    session_id = CURRENT_SESSION_ID.get()
    state = get_session_state(session_id)
    if state.monitor_task is None or state.monitor_task.done():
        return web.json_response({"ok": False, "error": "Monitoring is not running"})

    if state.timer_task and not state.timer_task.done():
        state.timer_task.cancel()
    state.timer_task = None
    state.auto_stop_at = None

    # Signal monitor loop task to shut down
    state.shutdown_event.set()
    ctx.append_gui_log("正在安全停止自動簽到監控服務...")
    
    try:
        await asyncio.wait_for(state.monitor_task, timeout=5.0)
    except asyncio.TimeoutError:
        ctx.append_gui_log("等待超時，強制取消監控任務。")
        state.monitor_task.cancel()
        try:
            await state.monitor_task
        except asyncio.CancelledError:
            pass
    except Exception as exc:
        ctx.append_gui_log(f"終止監控任務時發生異常: {exc}")

    state.monitor_task = None
    state.shutdown_event = None
    state.manual_stopped_at = time.time()
    ctx.append_gui_log("監控服務已完全停止。")
    return web.json_response({"ok": True})

async def auto_schedule_loop():
    while True:
        try:
            await asyncio.sleep(8)
            now_dt = ctx.current_datetime()
            today_idx = now_dt.weekday()  # 0=Mon..6=Sun
            current_time = now_dt.time()
            now_sec = time.time()

            for session_id, state in list(USER_SESSIONS.items()):
                if not getattr(state, 'auto_schedule_enabled', True):
                    continue

                # Don't auto-start if manually stopped in last 5 minutes (300s)
                if getattr(state, 'manual_stopped_at', 0) > 0 and (now_sec - state.manual_stopped_at) < 300:
                    continue

                # Check credentials
                active_profile = ctx.get_active_profile(state.CONFIG)
                if not ctx.has_real_credential(active_profile.user) or not ctx.has_real_credential(active_profile.passwd):
                    continue

                # Check schedule for today
                sched = state.CONFIG.get('operating', {}).get(today_idx, {})
                if not sched.get('enable', False):
                    continue

                ranges = sched.get('ranges', sched.get('range', []))
                is_in_schedule = ctx.is_within_any_schedule(ranges, current_time)
                is_running = state.monitor_task is not None and not state.monitor_task.done()

                if is_in_schedule and not is_running:
                    # Auto start!
                    state.shutdown_event = asyncio.Event()
                    state.monitor_task = asyncio.create_task(
                        ctx.app_main(input_enabled=False, external_shutdown_event=state.shutdown_event)
                    )
                    state.manual_stopped_at = 0.0
                    time_str = current_time.strftime("%H:%M")
                    ctx.append_gui_log(f"⏰ [排程自動開啟] 抵達設定上課時段（{time_str}），系統已自動啟動自動簽到監控服務！")
        except asyncio.CancelledError:
            break
        except Exception:
            pass


def get_local_ips():
    ips = ["127.0.0.1"]
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127."):
                ips.append(ip)
    except Exception:
        pass
    
    # fallback DGRAM probe
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        if ip not in ips:
            ips.append(ip)
        s.close()
    except Exception:
        pass
    return ips


async def run_gui_server(args) -> int:
    ctx.bootstrap_config()
    setup_session_isolation()
    
    host = args.host or '0.0.0.0'
    port = args.port or 8791
    open_browser = getattr(args, 'open', True)

    app = web.Application(middlewares=[session_middleware])
    app.router.add_get('/', serve_index)
    app.router.add_get('/favicon.ico', serve_favicon)
    app.router.add_get('/api/config', api_get_config)
    app.router.add_post('/api/config', api_save_config)
    app.router.add_post('/api/schedule', api_save_schedule)
    app.router.add_get('/api/status', api_get_status)
    app.router.add_post('/api/start', api_start_monitor)
    app.router.add_post('/api/stop', api_stop_monitor)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()

    # Start background cleanup and auto schedule runner
    asyncio.create_task(session_cleanup_loop())
    asyncio.create_task(auto_schedule_loop())

    # Determine connection URLs
    local_ips = get_local_ips()
    primary_ip = local_ips[1] if len(local_ips) > 1 else '127.0.0.1'
    local_url = f"http://127.0.0.1:{port}"
    lan_url = f"http://{primary_ip}:{port}"

    print("=" * 65)
    print("           ★  iClass 自動點名助手 Web GUI 伺服器已啟動  ★")
    print("=" * 65)
    print(f" 本地連線網址:  {local_url}")
    print(f" 手機/區域連線:  {lan_url}")
    print("=" * 65)
    print(" 說明: 請確保手機與電腦在同個 Wi-Fi 下，即可使用手機連線操作！")
    print(" [提示] 按 Ctrl + C 即可終止伺服器")
    print("=" * 65)

    if open_browser:
        try:
            webbrowser.open(local_url)
        except Exception:
            pass

    # Keep running
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        # Stop background task of all active sessions
        for state in list(USER_SESSIONS.values()):
            if state.monitor_task and not state.monitor_task.done():
                state.shutdown_event.set()
                try:
                    await state.monitor_task
                except Exception:
                    pass
        await runner.cleanup()
    
    return 0
