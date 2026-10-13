# Project_Index.md
# Auto-Rollcall-THU-TronClass — 全局架構索引

> 本文件由 AI Tech Lead 自動生成，作為專案的唯一架構藍圖。
> 最後更新：2026-06-09

---

## 1. 專案概覽

| 欄位 | 內容 |
|------|------|
| **專案名稱** | auto-rollcall-thu-tronclass |
| **版本** | v1.3a1 |
| **授權** | AGPL-3.0-or-later |
| **Python 需求** | >= 3.10 |
| **主要語言** | Python (後端) + HTML/CSS/JavaScript (Web GUI) |
| **部署目標** | 本機 Windows EXE、Hugging Face Spaces、任意 Python 環境 |

**核心功能**：TronClass 校園點名系統（東海 iLearn、淡江 iClass）全自動簽到工具，支援數字點名、雷達點名、QR 點名三種模式。

---

## 2. 目錄結構

```
auto-rollcall-thu-tronclass/
│
├── .docs/                          ← 📂 AI 開發文件目錄（本目錄）
│   ├── Project_Index.md
│   ├── Task_Plan.md
│   └── Dev_Status.md
│
├── troTHU/                         ← 📦 主套件目錄（所有業務邏輯）
│   │
│   ├── tron.py                     ← 程式進入點 (main())
│   ├── runtime_context.py          ← 🏛 中央全域狀態樞紐（最重要）
│   │
│   ├── ── CLI 層 ──
│   ├── cli_main.py                 ← CLI 命令路由器
│   ├── cli_parser.py               ← argparse 命令定義
│   ├── cli_accounts.py             ← account 子命令
│   ├── cli_app.py                  ← app 子命令（唯讀面板）
│   ├── cli_bot.py                  ← bot 子命令
│   ├── cli_courses.py              ← courses 子命令
│   ├── cli_provider.py             ← provider 子命令
│   ├── cli_qr.py                   ← qr 子命令
│   ├── cli_research.py             ← research 子命令（開發/除錯）
│   ├── cli_system.py               ← config/doctor/logs/status 子命令
│   ├── cli_teacher.py              ← teacher 子命令
│   │
│   ├── ── 設定層 ──
│   ├── config_runtime.py           ← 設定讀寫、正規化、bootstrap
│   ├── config_editor.py            ← 用記事本開設定檔
│   ├── config_view.py              ← 設定顯示格式化
│   ├── simple_config.py            ← 簡化版 config.yaml 解析器
│   ├── input_safety.py             ← 輸入欄位消毒（XSS/Injection 防護）
│   │
│   ├── ── 認證層 ──
│   ├── auth_runtime.py             ← 登入邏輯（HTTP SSO / CAS / 瀏覽器輔助）
│   ├── account_store.py            ← 帳號 Profile 管理 + Cookie 快取讀寫
│   ├── account_runtime_store.py    ← 帳號執行期狀態 JSON 持久化
│   ├── webview_sync.py             ← WebView Cookie 匯入同步
│   │
│   ├── ── 監控核心 ──
│   ├── monitor_runtime.py          ← 主監控迴圈（登入→排程→偵測→分流）
│   ├── rollcall_runtime.py         ← 點名分流與狀態管理
│   ├── rollcall_engine.py          ← 點名決策引擎（分類/決定/選取）
│   ├── rollcall_models.py          ← 點名資料模型（AttendanceType 等）
│   ├── rollcall_progress.py        ← 出席率查詢與進度追蹤
│   ├── logging_runtime.py          ← 日誌輸出 + GUI_LOGS 緩衝
│   │
│   ├── ── 點名類型實作 ──
│   ├── number_runtime.py           ← 數字點名（讀碼 + 暴力後備）
│   ├── number_rollcall.py          ← 數字點名資料模型
│   ├── radar_runtime.py            ← 雷達點名（空答案 + 全球定位後備）
│   ├── radar_rollcall.py           ← 雷達點名資料模型
│   ├── radar_solver.py             ← 局部 WGS84 多點定位求解器
│   ├── global_radar_solver.py      ← 全球 WGS84 定位演算法（零依賴）
│   ├── radar_map_assist.py         ← 雷達地圖輔助工具
│   ├── qr_rollcall.py              ← QR 點名資料模型
│   ├── qr_runtime.py               ← QR 手動提交 / 剪貼簿流程
│   ├── qr_teacher_runtime.py       ← QR 教師帳號輔助全自動流程
│   ├── teacher_rollcall.py         ← 教師端點名 API 工具
│   ├── pending_qr.py               ← Pending QR Registry 管理
│   ├── clipboard_qr.py             ← 剪貼簿 QR 自動讀取
│   │
│   ├── ── HTTP / 網路層 ──
│   ├── tron_http.py                ← TronClass HTTP Client + 登入流程
│   ├── course_discovery.py         ← 課程列表自動發現
│   ├── connection_probe.py         ← 網路連線診斷工具
│   │
│   ├── ── 提供者（學校）層 ──
│   ├── providers.py                ← 學校 Provider 定義（THU/TKU/TronClass/FJU）
│   │
│   ├── ── Web GUI 層 ──
│   ├── web_gui.py                  ← 🌐 Web GUI 伺服器（多用戶會話隔離）
│   ├── local_scanner.py            ← 本機 QR 掃描器 Web Server
│   ├── app_shell.py                ← 唯讀狀態面板 App Shell
│   ├── app_shell_dashboard.py      ← App Shell 儀表板
│   ├── app_shell_polish.py         ← App Shell UI 精緻化
│   ├── app_blueprint.py            ← App 架構藍圖生成器
│   ├── app_qr_experience.py        ← App QR 用戶體驗流程
│   │
│   ├── ── Bot / 通知層 ──
│   ├── bot_runtime.py              ← Bot 服務器主邏輯
│   ├── bot_handlers.py             ← Bot 指令處理器
│   ├── bot_status.py               ← Bot 狀態報告
│   ├── adapter_bridge.py           ← Bot Adapter 橋接器
│   ├── adapter_server.py           ← Bot HTTP Adapter 伺服器
│   ├── discord_adapter.py          ← Discord Interactions Adapter
│   ├── discord_gateway.py          ← Discord Gateway 模式
│   ├── line_adapter.py             ← LINE Webhook Adapter
│   ├── telegram_adapter.py         ← Telegram 單向通知
│   ├── notification_bus.py         ← 通知事件分發 Bus
│   ├── notification_delivery.py    ← 通知發送實作
│   │
│   ├── ── 狀態與診斷層 ──
│   ├── status_reports.py           ← 狀態快照與診斷報告
│   ├── observability.py            ← 可觀察性工具
│   ├── package_diagnostics.py      ← 套件診斷
│   ├── ux_tools.py                 ← UX 工具（日誌摘要、除錯包）
│   │
│   ├── ── 工具模組 ──
│   ├── runtime_helpers.py          ← 排程、時間、格式化輔助
│   ├── group_runtime.py            ← 群組帳號執行
│   ├── debug_capture.py            ← Debug 資料擷取
│   ├── research_sandbox.py         ← Research Mode API 探針
│   ├── research_mode.py            ← Research Mode 設定正規化
│   ├── release_builder.py          ← Release 打包工具
│   ├── release_checklist.py        ← Release 檢查清單
│   │
├── tests/                          ← 🧪 測試目錄（58 個測試檔案，574 個測試）
│   ├── fake_tron_server.py         ← 假 TronClass 伺服器（完全離線測試）
│   ├── test_session_isolation.py   ← Web GUI 會話隔離測試（新增）
│   └── test_*.py                   ← 各模組單元測試
│
├── config.yaml                     ← 用戶設定檔（超簡化格式）
├── config.advanced.yaml            ← 進階設定（真正的 YAML）
├── pyproject.toml                  ← 套件元資料與依賴定義
├── requirements.txt                ← 基礎依賴（aiohttp, PyYAML, PyNaCl）
├── auto-rollcall-thu-tronclass.spec ← PyInstaller 打包規格
└── README.md                       ← 使用者文件
```

---

## 3. 技術堆疊

### 後端
| 技術 | 版本 | 用途 |
|------|------|------|
| Python | >= 3.10 | 主要語言 |
| aiohttp | >= 3.9.5 | 非同步 HTTP Client + Web Server |
| PyYAML | >= 6.0.2 | 進階設定檔解析 |
| PyNaCl | >= 1.5.0 | Discord Interactions 簽章驗證 |
| keyring | >= 24 (選用) | 系統金鑰圈帳密儲存 |
| playwright | >= 1.44 (選用) | 瀏覽器輔助登入（TKU SSO） |
| opencv + Pillow | (選用) | QR 圖片解碼 |
| PyInstaller | >= 6 (選用) | Windows EXE 打包 |

### 前端（Web GUI）
| 技術 | 用途 |
|------|------|
| Vanilla HTML/CSS/JavaScript | 嵌入在 `web_gui.py` Python 字串中 |
| Google Fonts (Outfit, Noto Sans TC) | 字型 |
| 玻璃擬態設計 (Glassmorphism) | UI 風格 |
| CSS Variables + Animations | 主題與動效 |
| Fetch API + setInterval | 非同步狀態輪詢 |

### 測試
| 技術 | 用途 |
|------|------|
| unittest | 標準測試框架 |
| fake_tron_server.py | 完全離線的假 TronClass 伺服器 |
| contextvars | 會話隔離測試 |

---

## 4. 核心模組功能定義

### 4.1 `runtime_context.py` — 中央樞紐 ⭐

這是整個系統最重要的檔案。它的職責：
1. **持有所有全域執行狀態**（`CONFIG`, `MONITOR_STATUS`, `GUI_LOGS`, `IS_LOGGING_IN` 等）
2. **懶載入模組命名空間**：透過 `_LEGACY_EXPORTS` 字典讓所有模組能用 `ctx.foo()` 呼叫任意函式，不需要循環 import
3. **定義核心資料結構**：`LoginResult`, `DEFAULT_CONFIG`, `DEFAULT_USER_AGENTS` 等

**重要規則**：新增要用 `ctx.foo` 呼叫的函式，必須在 `_LEGACY_EXPORTS` 字典中註冊。

### 4.2 Web GUI 會話隔離架構（最近新增）

```python
# web_gui.py 中的關鍵架構元素

CURRENT_SESSION_ID: ContextVar  # 每個 HTTP request 的 session ID 綁定
USER_SESSIONS: Dict[str, UserSessionState]  # 全域 session 字典

class UserSessionState:
    # 每個用戶獨立的執行狀態副本
    CONFIG, MONITOR_STATUS, GUI_LOGS, cookie_cache,
    monitor_task, shutdown_event, IS_LOGGING_IN, ...

class SessionProxyDict(dict):  # 代理 CONFIG/MONITOR_STATUS 等 dict 型變數
class SessionProxyList(list):  # 代理 GUI_LOGS/NOTIFICATION_SINKS 等 list 型變數
class SessionIsolatedModule(types.ModuleType):  # 攔截 ctx.XXX 讀寫

def setup_session_isolation():  # 啟動時安裝模組代理 + Mock I/O 函式
```

**隔離原理**：`ctx.__class__` 動態替換為 `SessionIsolatedModule`，配合 `contextvars.ContextVar` 讓每個 `aiohttp` request 的非同步執行鏈都能找到自己的 session state。

---

## 5. Provider（學校）系統

```
providers.py 定義的 PROVIDERS 字典：

thu       → 東海大學 iLearn (CAS 登入)          [ready]
tku       → 淡江大學 iClass (SSO 登入, 預設)    [ready]
tronclass → TronClass 公有雲 (Email 登入)       [ready]
fju       → 輔仁大學 (手動 Cookie，隱藏)        [ready]
```

**auth_flow 類型**：
- `thu_cas` — THU CAS SSO 自動登入
- `tku_sso_browser` — TKU HTTP SSO + 瀏覽器後備
- `public_cloud_email` — Email/Password 表單 POST
- `manual_cookie_only` — 只接受手動 Cookie 匯入

---

## 6. 核心 API 端點（TronClass）

| API | 用途 |
|-----|------|
| `GET /api/radar/rollcalls?api_version=1.1.0` | 偵測進行中的點名 |
| `GET /api/rollcall/{id}/student_rollcalls` | 讀取數字點名碼 |
| `PUT /api/rollcall/{id}/answer_number_rollcall` | 送出數字點名 |
| `PUT /api/rollcall/{id}/answer` | 送出雷達點名（空答案 `{}`）|
| `PUT /api/rollcall/{id}/answer?api_version=1.76` | 送出帶座標的雷達點名 |
| `GET /api/rollcall/{id}/lite` | 取得雷達 beacon 資訊 |
| `GET /api/rollcall/{id}/answers` | 確認簽到狀態 |
| `POST /api/course/{id}/rollcall` | 教師建立 QR 點名 |
| `GET /api/course/{cid}/rollcall/{rid}/qr_code` | 取得 QR data（教師端）|
| `PUT /api/rollcall/{id}/answer_qr_rollcall` | 送出 QR 點名（學生端）|
| `GET /api/my-courses` | 課程列表 |

---

## 7. Web GUI API 端點

| 端點 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 返回 SPA HTML |
| `/favicon.ico` | GET | 空回應（204） |
| `/api/config` | GET | 取得當前會話設定 |
| `/api/config` | POST | 儲存帳號/學校設定 |
| `/api/schedule` | POST | 儲存每週時段設定 |
| `/api/status` | GET | 取得監控狀態 + 日誌（每 1.5 秒輪詢）|
| `/api/start` | POST | 啟動監控（自動先儲存設定）|
| `/api/stop` | POST | 停止監控 |

---

## 8. 設定檔結構

### `config.yaml`（超簡化格式，非標準 YAML）
```
now: {帳號學號或群組名}
account:
  user: {學號}
  passwd: {密碼}
  school: {THU|TKU}
teacher:
  user: {教師帳號}
  passwd: {密碼}
  school: {TRONCLASS|THU|TKU}
group:
  class: A
    user: {帳號}
operating:
  {0-6(日-六)}:
    enable: true
    range:
    - HH:MM - HH:MM
```

### `config.advanced.yaml`（真正的 YAML）
包含：時區、number/radar 細部參數、Bot 通知設定、SSL 設定等。

---

## 9. 資料流向圖

```
用戶輸入(config.yaml / Web GUI)
    ↓
config_runtime.py (bootstrap_config / normalize_config)
    ↓
runtime_context.py (CONFIG 全域變數)
    ↓
auth_runtime.py (login → aiohttp session)
    ↓
monitor_runtime.py (主迴圈：排程判斷 → rollcall 偵測)
    ↓
rollcall_runtime.py (分流：number / radar / qr)
    ↓
┌──────────────────────────────────────────┐
│ number_runtime.py  │  radar_runtime.py   │  qr_runtime.py / qr_teacher_runtime.py │
└──────────────────────────────────────────┘
    ↓
tron_http.py (送出 HTTP 請求到 TronClass)
    ↓
logging_runtime.py (log_print → GUI_LOGS 緩衝)
    ↓
web_gui.py /api/status (回傳給前端展示)
```

---

## 10. 測試指令速查

```bash
# 語法檢查
python -m py_compile troTHU/tron.py troTHU/runtime_context.py troTHU/cli_main.py

# 完整測試套件（574 個測試，完全離線）
python -m unittest discover -v

# 會話隔離專屬測試（新增）
python -m unittest tests/test_session_isolation.py

# 啟動 Web GUI（本地開發）
python -m troTHU.tron gui --port 8791

# 打包 Windows EXE
python -m troTHU.tron release-build --dry-run --json
```

---

## 11. 關鍵路徑速查（Debug 用）

| 問題場景 | 查看的檔案 |
|----------|------------|
| 登入失敗 | `auth_runtime.py`, `tron_http.py` |
| 排程不對 | `config_runtime.py` (`get_schedule_for_day`), `runtime_helpers.py` |
| 數字點名失敗 | `number_runtime.py`, `number_rollcall.py` |
| 雷達點名失敗 | `radar_runtime.py`, `radar_solver.py`, `global_radar_solver.py` |
| QR 點名失敗 | `qr_runtime.py`, `qr_teacher_runtime.py` |
| Web GUI 狀態不更新 | `web_gui.py` (`api_get_status`), `logging_runtime.py` |
| 設定讀取異常 | `config_runtime.py` (`bootstrap_config`), `simple_config.py` |
| 多用戶 session 混亂 | `web_gui.py` (`SessionProxyDict`, `setup_session_isolation`) |
| 新增學校 Provider | `providers.py` (`PROVIDERS` 字典) |
| Bot 通知失敗 | `notification_delivery.py`, `notification_bus.py` |
