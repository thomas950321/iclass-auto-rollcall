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

HTML_CONTENT = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>iClass 自動簽到助手</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Noto+Sans+TC:wght@300;400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0b0f19;
            --card-bg: rgba(22, 28, 45, 0.65);
            --card-border: rgba(255, 255, 255, 0.08);
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            --primary-glow: rgba(79, 70, 229, 0.4);
            --accent: #6366f1;
            --success: #10b981;
            --success-glow: rgba(16, 185, 129, 0.3);
            --danger: #ef4444;
            --danger-glow: rgba(239, 68, 68, 0.3);
            --warning: #f59e0b;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            user-select: none;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            font-family: 'Outfit', 'Noto Sans TC', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            overflow-x: hidden;
            position: relative;
        }

        /* Ambient background blobs */
        body::before, body::after {
            content: '';
            position: absolute;
            width: 300px;
            height: 300px;
            border-radius: 50%;
            z-index: -1;
            filter: blur(80px);
            opacity: 0.45;
        }

        body::before {
            background: radial-gradient(circle, #4f46e5 0%, transparent 70%);
            top: -50px;
            left: -100px;
        }

        body::after {
            background: radial-gradient(circle, #10b981 0%, transparent 70%);
            bottom: 50px;
            right: -100px;
        }

        header {
            width: 100%;
            max-width: 500px;
            padding: 24px 20px 10px;
            text-align: center;
            position: relative;
        }

        .logo-container {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 8px;
        }

        h1 {
            font-size: 24px;
            font-weight: 700;
            letter-spacing: -0.5px;
            background: linear-gradient(135deg, #ffffff 30%, #a5b4fc 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .subtitle {
            font-size: 13px;
            color: var(--text-secondary);
            margin-top: 4px;
        }

        .container {
            width: 100%;
            max-width: 500px;
            padding: 10px 16px 40px;
            display: flex;
            flex-direction: column;
            gap: 16px;
            z-index: 1;
        }

        .card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 18px;
            padding: 20px;
            backdrop-filter: blur(16px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .card-title {
            font-size: 15px;
            font-weight: 600;
            margin-bottom: 14px;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .card-title::before {
            content: '';
            display: inline-block;
            width: 4px;
            height: 14px;
            background: var(--accent);
            border-radius: 2px;
        }

        /* Form Controls */
        .form-group {
            margin-bottom: 14px;
            position: relative;
        }

        .form-group:last-child {
            margin-bottom: 0;
        }

        label {
            display: block;
            font-size: 12px;
            font-weight: 500;
            color: var(--text-secondary);
            margin-bottom: 6px;
        }

        select, input[type="text"], input[type="password"] {
            width: 100%;
            height: 46px;
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 0 14px;
            color: #ffffff;
            font-family: inherit;
            font-size: 14px;
            outline: none;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }

        select:focus, input:focus {
            border-color: var(--accent);
            box-shadow: 0 0 10px var(--primary-glow);
        }

        .password-container {
            position: relative;
        }

        .toggle-password {
            position: absolute;
            right: 12px;
            top: 50%;
            transform: translateY(-50%);
            background: none;
            border: none;
            color: var(--text-secondary);
            cursor: pointer;
            padding: 4px;
            font-size: 12px;
        }

        /* Schedule Grid */
        .schedule-grid {
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-top: 10px;
        }

        .day-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 12px;
            background: rgba(15, 23, 42, 0.4);
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.03);
        }

        .day-label {
            font-size: 13px;
            font-weight: 500;
        }

        .day-controls {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .time-range-input {
            width: 120px;
            height: 30px;
            background: rgba(10, 15, 26, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            color: #ffffff;
            font-size: 12px;
            text-align: center;
            outline: none;
        }

        /* Toggle switch */
        .switch {
            position: relative;
            display: inline-block;
            width: 38px;
            height: 22px;
        }

        .switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }

        .slider {
            position: absolute;
            cursor: pointer;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: #374151;
            transition: .3s;
            border-radius: 34px;
        }

        .slider:before {
            position: absolute;
            content: "";
            height: 16px;
            width: 16px;
            left: 3px;
            bottom: 3px;
            background-color: white;
            transition: .3s;
            border-radius: 50%;
        }

        input:checked + .slider {
            background-color: var(--accent);
        }

        input:checked + .slider:before {
            transform: translateX(16px);
        }

        /* Action Buttons */
        .btn {
            width: 100%;
            height: 48px;
            border-radius: 12px;
            border: none;
            font-family: inherit;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.25s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .btn-primary {
            background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%);
            color: #ffffff;
            box-shadow: 0 4px 15px var(--primary-glow);
        }

        .btn-primary:active {
            transform: scale(0.98);
        }

        /* Start/Stop Button styles */
        .btn-start {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: #ffffff;
            box-shadow: 0 4px 15px var(--success-glow);
            font-size: 16px;
            height: 52px;
            border-radius: 14px;
        }

        .btn-stop {
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            color: #ffffff;
            box-shadow: 0 4px 15px var(--danger-glow);
            font-size: 16px;
            height: 52px;
            border-radius: 14px;
        }

        /* Status segment */
        .status-panel {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            font-weight: 600;
            padding: 4px 10px;
            border-radius: 30px;
        }

        .status-stopped {
            background: rgba(239, 68, 68, 0.15);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.25);
        }

        .status-running {
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.25);
            animation: pulse-border 2s infinite;
        }

        .status-item {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .status-label {
            font-size: 11px;
            color: var(--text-secondary);
        }

        .status-val {
            font-size: 14px;
            font-weight: 500;
        }

        /* Console Log box */
        .console-card {
            display: flex;
            flex-direction: column;
        }

        .console-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }

        .console-box {
            height: 180px;
            background: rgba(10, 15, 26, 0.85);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 12px;
            font-family: Consolas, Monaco, monospace;
            font-size: 11px;
            line-height: 1.4;
            color: #d1d5db;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-all;
        }

        .log-line {
            margin-bottom: 4px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.02);
            padding-bottom: 2px;
        }

        .log-success { color: #34d399; }
        .log-warning { color: #fbbf24; }
        .log-danger { color: #f87171; }
        .log-info { color: #60a5fa; }

        .search-input {
            height: 28px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            padding: 0 8px;
            color: #fff;
            font-size: 11px;
            outline: none;
            width: 100px;
        }

        /* Modal / Toast notification */
        .toast {
            position: fixed;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%) translateY(100px);
            background: rgba(17, 24, 39, 0.9);
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 12px 24px;
            border-radius: 30px;
            font-size: 13px;
            z-index: 999;
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
            display: flex;
            align-items: center;
            gap: 8px;
            white-space: nowrap;
        }

        .toast.show {
            transform: translateX(-50%) translateY(0);
        }

        /* QR block for scan */
        .qr-section {
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            padding: 10px 0;
        }

        .qr-canvas-holder {
            background: white;
            padding: 8px;
            border-radius: 12px;
            margin-bottom: 10px;
            display: inline-block;
        }

        .qr-description {
            font-size: 12px;
            color: var(--text-secondary);
            max-width: 280px;
        }

        @keyframes pulse-border {
            0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4); }
            70% { box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
            100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }

        .footer {
            margin-top: auto;
            padding: 20px;
            text-align: center;
            font-size: 11px;
            color: rgba(255, 255, 255, 0.25);
        }
    </style>
</head>
<body>
    <header>
        <div class="logo-container">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-right: 6px;">
                <path d="M12 2L2 7L12 12L22 7L12 2Z" fill="#6366F1"/>
                <path d="M2 17L12 22L22 17" stroke="#6366F1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M2 12L12 17L22 12" stroke="#6366F1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <h1>iClass 自動簽到助手</h1>
        </div>
        <div class="subtitle">淡江大學 (TKU) 專屬全自動監控簽到系統</div>
    </header>

    <div class="container">
        <!-- Status Panel -->
        <div class="card status-panel">
            <div class="status-item">
                <div class="status-label">監控狀態</div>
                <div id="statusBadge" class="status-badge status-stopped">
                    <span id="statusIndicator">●</span> <span id="statusText">已停止</span>
                </div>
            </div>
            <div class="status-item" style="text-align: center;">
                <div class="status-label">檢查次數</div>
                <div id="checkCount" class="status-val">0</div>
            </div>
            <div class="status-item" style="text-align: right;">
                <div class="status-label">執行階段</div>
                <div id="phaseText" class="status-val">休眠中</div>
            </div>
        </div>

        <!-- Master Toggle -->
        <button id="toggleBtn" class="btn btn-start">啟動監控</button>

        <!-- Configuration Card -->
        <div class="card">
            <div class="card-title">帳號與設定</div>
            
            <div class="form-group">
                <label for="schoolSelect">學校</label>
                <select id="schoolSelect">
                    <option value="tku" selected>淡江大學 (TKU)</option>
                    <option value="thu">東海大學 (THU)</option>
                    <option value="tronclass">TronClass 公有雲</option>
                </select>
            </div>

            <div class="form-group">
                <label for="userVal">帳號 (學號)</label>
                <input type="text" id="userVal" placeholder="請輸入學號">
            </div>

            <div class="form-group">
                <label for="passwdVal">密碼</label>
                <div class="password-container">
                    <input type="password" id="passwdVal" placeholder="請輸入密碼">
                    <button type="button" id="togglePass" class="toggle-password">顯示</button>
                </div>
            </div>

            <button id="saveConfigBtn" class="btn btn-primary" style="margin-top: 10px; height: 38px; font-size: 13px;">保存帳號設定</button>
        </div>

        <!-- Operating Schedule -->
        <div class="card">
            <div class="card-title">每週上課排程監控時段</div>
            <div style="font-size: 11px; color: var(--text-secondary); margin-top: -6px; margin-bottom: 10px;">
                僅在設定好的時間區間內才會自動輪詢點名，其餘時段會自動休眠省電。
            </div>
            <div class="schedule-grid">
                <!-- Days Mon..Sun -->
                <div class="day-row" data-day="0">
                    <div class="day-label">星期一</div>
                    <div class="day-controls">
                        <input type="text" class="time-range-input" value="08:00 - 18:00">
                        <label class="switch">
                            <input type="checkbox" checked>
                            <span class="slider"></span>
                        </label>
                    </div>
                </div>
                <div class="day-row" data-day="1">
                    <div class="day-label">星期二</div>
                    <div class="day-controls">
                        <input type="text" class="time-range-input" value="08:00 - 18:00">
                        <label class="switch">
                            <input type="checkbox" checked>
                            <span class="slider"></span>
                        </label>
                    </div>
                </div>
                <div class="day-row" data-day="2">
                    <div class="day-label">星期三</div>
                    <div class="day-controls">
                        <input type="text" class="time-range-input" value="08:00 - 18:00">
                        <label class="switch">
                            <input type="checkbox" checked>
                            <span class="slider"></span>
                        </label>
                    </div>
                </div>
                <div class="day-row" data-day="3">
                    <div class="day-label">星期四</div>
                    <div class="day-controls">
                        <input type="text" class="time-range-input" value="08:00 - 18:00">
                        <label class="switch">
                            <input type="checkbox" checked>
                            <span class="slider"></span>
                        </label>
                    </div>
                </div>
                <div class="day-row" data-day="4">
                    <div class="day-label">星期五</div>
                    <div class="day-controls">
                        <input type="text" class="time-range-input" value="08:00 - 18:00">
                        <label class="switch">
                            <input type="checkbox" checked>
                            <span class="slider"></span>
                        </label>
                    </div>
                </div>
                <div class="day-row" data-day="5">
                    <div class="day-label">星期六</div>
                    <div class="day-controls">
                        <input type="text" class="time-range-input" value="08:00 - 18:00">
                        <label class="switch">
                            <input type="checkbox" checked>
                            <span class="slider"></span>
                        </label>
                    </div>
                </div>
                <div class="day-row" data-day="6">
                    <div class="day-label">星期日</div>
                    <div class="day-controls">
                        <input type="text" class="time-range-input" value="08:00 - 18:00">
                        <label class="switch">
                            <input type="checkbox" checked>
                            <span class="slider"></span>
                        </label>
                    </div>
                </div>
            </div>
            <button id="saveScheduleBtn" class="btn btn-primary" style="margin-top: 14px; height: 38px; font-size: 13px;">儲存上課排程</button>
        </div>

        <!-- Live Console Logs -->
        <div class="card console-card">
            <div class="console-header">
                <div class="card-title" style="margin-bottom: 0;">即時執行紀錄</div>
                <input type="text" id="logFilter" class="search-input" placeholder="搜尋紀錄...">
            </div>
            <div id="consoleBox" class="console-box">Loading...</div>
        </div>
    </div>

    <div class="toast" id="toast">
        <span id="toastIcon">ℹ️</span>
        <span id="toastText">訊息</span>
    </div>

    <footer class="footer">
        iClass Auto Rollcall Helper v1.3 &copy; 2026
    </footer>



    <script>
        // Main Application Scripts
        let isRunning = false;
        let isFetchingLogs = false;
        const currentUrl = window.location.href;

        // Elements
        const toggleBtn = document.getElementById('toggleBtn');
        const statusBadge = document.getElementById('statusBadge');
        const statusText = document.getElementById('statusText');
        const checkCountEl = document.getElementById('checkCount');
        const phaseTextEl = document.getElementById('phaseText');
        const consoleBox = document.getElementById('consoleBox');
        const userVal = document.getElementById('userVal');
        const passwdVal = document.getElementById('passwdVal');
        const schoolSelect = document.getElementById('schoolSelect');
        const togglePass = document.getElementById('togglePass');
        const logFilter = document.getElementById('logFilter');

        // Show toast notifications
        function showToast(message, type = 'info') {
            const toast = document.getElementById('toast');
            const toastText = document.getElementById('toastText');
            const toastIcon = document.getElementById('toastIcon');
            
            toastText.textContent = message;
            toastIcon.textContent = type === 'success' ? '✅' : (type === 'error' ? '❌' : 'ℹ️');
            
            toast.classList.add('show');
            setTimeout(() => {
                toast.classList.remove('show');
            }, 3000);
        }

        // Toggle password visibility
        togglePass.addEventListener('click', () => {
            if (passwdVal.type === 'password') {
                passwdVal.type = 'text';
                togglePass.textContent = '隱藏';
            } else {
                passwdVal.type = 'password';
                togglePass.textContent = '顯示';
            }
        });

        // Initialize state
        async function fetchConfig() {
            try {
                const response = await fetch('/api/config');
                const data = await response.json();
                if (data.ok) {
                    userVal.value = data.config.user || '';
                    passwdVal.value = data.config.passwd || '';
                    schoolSelect.value = data.config.school || 'tku';

                    // Update schedule switches and ranges
                    const operating = data.config.operating || {};
                    for (let day = 0; day < 7; day++) {
                        const dayRow = document.querySelector(`.day-row[data-day="${day}"]`);
                        if (dayRow && operating[day]) {
                            const rangeInput = dayRow.querySelector('.time-range-input');
                            const checkbox = dayRow.querySelector('input[type="checkbox"]');
                            
                            checkbox.checked = operating[day].enable;
                            if (operating[day].ranges && operating[day].ranges.length > 0) {
                                rangeInput.value = operating[day].ranges[0];
                            } else if (operating[day].range) {
                                rangeInput.value = operating[day].range;
                            }
                        }
                    }
                }
            } catch (err) {
                console.error("Fetch config failed", err);
            }
        }

        async function fetchStatus() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                if (data.ok) {
                    isRunning = data.running;
                    checkCountEl.textContent = data.status.check_count || 0;
                    
                    // Update execution phase description in Traditional Chinese
                    let phaseDesc = "休眠中";
                    if (data.status.phase === "monitoring") {
                        phaseDesc = "監控點名中";
                    } else if (data.status.phase === "logging_in") {
                        phaseDesc = "登入中";
                    } else if (data.status.phase === "standby") {
                        phaseDesc = "休眠時段";
                    }
                    
                    if (data.status.detail) {
                        phaseDesc += ` (${data.status.detail})`;
                    }
                    phaseTextEl.textContent = phaseDesc;

                    // Update controls
                    if (isRunning) {
                        toggleBtn.textContent = '停止監控';
                        toggleBtn.className = 'btn btn-stop';
                        statusBadge.className = 'status-badge status-running';
                        statusText.textContent = '監控中';
                    } else {
                        toggleBtn.textContent = '啟動監控';
                        toggleBtn.className = 'btn btn-start';
                        statusBadge.className = 'status-badge status-stopped';
                        statusText.textContent = '已停止';
                    }

                    // Render logs
                    renderLogs(data.logs);
                }
            } catch (err) {
                console.error("Fetch status failed", err);
            }
        }

        // Render console log outputs
        function renderLogs(logs) {
            if (!logs || logs.length === 0) {
                consoleBox.textContent = "尚無執行紀錄";
                return;
            }
            
            const filter = logFilter.value.toLowerCase().trim();
            const lines = [];
            
            logs.forEach(log => {
                if (filter && !log.toLowerCase().includes(filter)) {
                    return;
                }
                
                let className = "log-info";
                if (log.includes("成功") || log.includes("完成") || log.includes("簽到")) {
                    className = "log-success";
                } else if (log.includes("警告") || log.includes("重試") || log.includes("等待")) {
                    className = "log-warning";
                } else if (log.includes("錯誤") || log.includes("失敗") || log.includes("異常")) {
                    className = "log-danger";
                }
                
                lines.push(`<div class="log-line ${className}">${escapeHtml(log)}</div>`);
            });
            
            const atBottom = consoleBox.scrollHeight - consoleBox.clientHeight <= consoleBox.scrollTop + 40;
            consoleBox.innerHTML = lines.join('') || "無相符的紀錄";
            
            if (atBottom || isFetchingLogs === false) {
                consoleBox.scrollTop = consoleBox.scrollHeight;
                isFetchingLogs = true; // Flag we completed first scroll
            }
        }

        function escapeHtml(text) {
            return text
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }

        // Save Config Handlers
        document.getElementById('saveConfigBtn').addEventListener('click', async () => {
            const user = userVal.value.trim();
            const passwd = passwdVal.value.trim();
            const school = schoolSelect.value;

            if (!user || !passwd) {
                showToast("學號與密碼不能為空！", "error");
                return;
            }

            try {
                const response = await fetch('/api/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user, passwd, school })
                });
                const data = await response.json();
                if (data.ok) {
                    showToast("帳號設定儲存成功！", "success");
                    fetchConfig();
                } else {
                    showToast(data.error || "儲存失敗", "error");
                }
            } catch (err) {
                showToast("網路連線錯誤", "error");
            }
        });

        // Save Schedule Handlers
        document.getElementById('saveScheduleBtn').addEventListener('click', async () => {
            const operating = {};
            for (let day = 0; day < 7; day++) {
                const dayRow = document.querySelector(`.day-row[data-day="${day}"]`);
                const rangeInput = dayRow.querySelector('.time-range-input');
                const checkbox = dayRow.querySelector('input[type="checkbox"]');
                
                operating[day] = {
                    enable: checkbox.checked,
                    range: rangeInput.value.trim() || "00:00 - 00:00"
                };
            }

            try {
                const response = await fetch('/api/schedule', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ operating })
                });
                const data = await response.json();
                if (data.ok) {
                    showToast("上課監控排程儲存成功！", "success");
                    fetchConfig();
                } else {
                    showToast(data.error || "儲存失敗", "error");
                }
            } catch (err) {
                showToast("網路連線錯誤", "error");
            }
        });

        // Toggle Monitor Loop
        toggleBtn.addEventListener('click', async () => {
            if (!isRunning) {
                // Auto save credentials first
                const user = userVal.value.trim();
                const passwd = passwdVal.value.trim();
                const school = schoolSelect.value;

                if (!user || !passwd) {
                    showToast("學號與密碼不能為空！", "error");
                    return;
                }

                try {
                    const saveConfRes = await fetch('/api/config', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user, passwd, school })
                    });
                    const saveConfData = await saveConfRes.json();
                    if (!saveConfData.ok) {
                        showToast(saveConfData.error || "自動儲存帳號設定失敗", "error");
                        return;
                    }
                    
                    // Auto save schedule as well
                    const operating = {};
                    for (let day = 0; day < 7; day++) {
                        const dayRow = document.querySelector(`.day-row[data-day="${day}"]`);
                        const rangeInput = dayRow.querySelector('.time-range-input');
                        const checkbox = dayRow.querySelector('input[type="checkbox"]');
                        
                        operating[day] = {
                            enable: checkbox.checked,
                            range: rangeInput.value.trim() || "08:00 - 18:00"
                        };
                    }
                    const saveSchedRes = await fetch('/api/schedule', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ operating })
                    });
                    const saveSchedData = await saveSchedRes.json();
                    if (!saveSchedData.ok) {
                        showToast(saveSchedData.error || "自動儲存排程失敗", "error");
                        return;
                    }
                } catch (err) {
                    showToast("自動儲存設定失敗，請手動點擊保存按鈕", "error");
                    return;
                }
            }

            const url = isRunning ? '/api/stop' : '/api/start';
            toggleBtn.disabled = true;
            try {
                const response = await fetch(url, { method: 'POST' });
                const data = await response.json();
                if (data.ok) {
                    isRunning = !isRunning;
                    showToast(isRunning ? "監控服務已啟動" : "監控服務已停止", "success");
                    fetchStatus();
                } else {
                    showToast(data.error || "操作失敗", "error");
                }
            } catch (err) {
                showToast("連線異常", "error");
            } finally {
                toggleBtn.disabled = false;
            }
        });

        // Filter logs locally
        logFilter.addEventListener('input', () => {
            fetchStatus();
        });

        // Load initialization config
        fetchConfig();
        fetchStatus();
        
        // Loop poll status
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
    return ctx.AccountRuntimeSnapshot(store_status="missing")

def mock_log(*args, **kwargs):
    return True


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
    ctx.__dict__['GUI_LOGS'] = SessionProxyList('GUI_LOGS', ctx.GUI_LOGS)
    ctx.__dict__['NOTIFICATION_SINKS'] = SessionProxyList('NOTIFICATION_SINKS', ctx.NOTIFICATION_SINKS)

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
    # Retrieve current active profile details
    active_profile = ctx.get_active_profile(ctx.CONFIG)
    school = ctx.CONFIG.get('provider', {}).get('current', 'tku')

    # Convert internal schedule structure (Mon..Sun -> 0..6)
    # Mon=0 -> Sun=6
    operating = {}
    for internal_day in range(7):
        # Default config fallback
        schedule = ctx.CONFIG['operating'].get(internal_day, {"enable": True, "range": ["08:00 - 18:00"]})
        ranges = schedule.get("ranges", schedule.get("range", ["08:00 - 18:00"]))
        if isinstance(ranges, str):
            ranges = [ranges]
        
        # We send it simply as day index (Mon=0, ..., Sun=6)
        operating[internal_day] = {
            "enable": bool(schedule.get("enable", True)),
            "ranges": ranges
        }

    return web.json_response({
        "ok": True,
        "config": {
            "user": active_profile.user,
            "passwd": active_profile.passwd,
            "school": school,
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
        data = await request.json()
        operating_data = data.get("operating", {})

        # operating is formatted as {"0": {"enable": true, "range": "08:00 - 18:00"}}
        # We map keys to integer internal days Mon(0)..Sun(6)
        for day_str, value in operating_data.items():
            day_idx = int(day_str)
            if 0 <= day_idx <= 6:
                enable = bool(value.get("enable", True))
                range_str = str(value.get("range", "08:00 - 18:00"))
                
                # Update in ctx.CONFIG
                ctx.CONFIG['operating'][day_idx] = {
                    "enable": enable,
                    "range": ctx.normalize_schedule_range(range_str, ["00:00", "00:00"]),
                    "ranges": ctx.normalize_schedule_ranges(range_str, [["00:00", "00:00"]])
                }

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
        return web.json_response({"ok": False, "error": "尚未設定有效的學號與密碼"})

    # Start the standard asyncio loop in the background
    state.shutdown_event = asyncio.Event()
    state.monitor_task = asyncio.create_task(ctx.app_main(input_enabled=False, external_shutdown_event=state.shutdown_event))
    
    ctx.append_gui_log("Web GUI 已觸發監控啟動。")
    return web.json_response({"ok": True})

async def api_stop_monitor(request):
    session_id = CURRENT_SESSION_ID.get()
    state = get_session_state(session_id)
    if state.monitor_task is None or state.monitor_task.done():
        return web.json_response({"ok": False, "error": "Monitoring is not running"})

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
    ctx.append_gui_log("監控服務已完全停止。")
    return web.json_response({"ok": True})


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

    # Start the session cleaner in the background
    asyncio.create_task(session_cleanup_loop())

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
