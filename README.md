---
title: iClass Auto Rollcall
emoji: 📋
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
license: agpl-3.0
short_description: iClass / TronClass 全自動簽到助手（東海 iLearn / 淡江 iClass）
---

<div align="center">

# iClass Auto Rollcall (iClass 自動簽到助手)

**專為 TronClass 架構設計的校園自動簽到與點名監控工具**

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](./LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20Docker-lightgrey.svg)]()

</div>

---

## 專案簡介

Auto-Rollcall-THU-TronClass 是一套針對採用 TronClass 系統之大專院校（如東海大學 iLearn、淡江大學 iClass 及公有雲體系）開發的自動化點名輔助程式。程式能在指定課堂時段內常駐監控點名事件，並自動完成簽到流程，解決因網路壅塞、介面延遲或分心而錯失簽到時效的問題。

本專案支援數字點名、雷達定位點名與動態 QR 碼點名。系統內建誤觸防護門檻，並具備純 Python 實作的 WGS84 座標反推演算法，確保在各種極端情境下均能穩定運作。

> 安全提示：本工具僅供個人修課與技術研究使用。請遵守校園與課堂規範，切勿將包含帳號密碼、工作階段 Cookie 或憑證的設定檔與日誌外流。

## 核心優勢

- 穩定可靠的數字點名自動化：優先透過學生端介面直接解析伺服器回傳之簽到碼，秒級完成提交；若介面調整則自動切換至防限流保護的容錯試驗機制。
- 零依賴的全球定位備援演算法：雷達簽到支援伺服器驗證容錯，並內建純 Python 打造之 WGS84 橢球多點定位引擎，可藉由伺服器距離回饋在不依賴任何外部數學函式庫的前提下精準反推教室座標。
- 靈活完整的動態 QR 處理機制：支援剪貼簿即時辨識與手動輸入，並具備教師端動態 Token 即時同步模式，克服前端 QR 碼定時輪換之技術限制。

## 運作原理

程式在偵測到點名事件後，依循以下邏輯進行決策與執行：

1. 簽到率防誤觸門檻：點名發起後，程式預設監控班級簽到率，待簽到比例達標（預設為 15%）後始執行簽到，避免教師誤觸點名立即關閉時產生無效紀錄。若有即時簽到需求，可透過參數直接關閉門檻限制。
2. 數字點名解析流程：利用學生端點名資訊介面取得伺服器隨附之四位數字點名碼並立即送出。當伺服器未回傳點名碼時，啟動具備冷卻降頻機制的受限並行重試流程。
3. 雷達定位與座標推算：預設採用無座標空答案完成驗證。若伺服器強制檢查座標，程式會向多個方位發送探測請求，並利用伺服器回傳之距離誤差值，在 WGS84 座標系上透過穩健最小平方法求解教室經緯度。
4. QR 碼動態同步：若配置教師權限帳號，系統在偵測到課堂 QR 點名時同步發起虛擬點名取得有效之動態 Token，於有效時間窗口內完成學生端簽到後自動關閉臨時點名。

## 快速開始

### Windows 預編譯版本

1. 前往 Releases 頁面下載最新版本壓縮檔（`THU_Auto_Rollcall-*-windows-x64.zip`）。
2. 解壓縮至獨立資料夾（請勿於壓縮檔內部直接執行）。
3. 執行 `auto-rollcall-thu-tronclass.exe`。
4. 首次啟動將於同層目錄建立 `config.yaml`、`state/` 與 `log/`。在主控台按下任意鍵即可開啟文字編輯器填寫帳號資訊，儲存後程式自動套用新設定。

### 原始碼執行

環境需求：Python 3.10 或更新版本。

```bash
# 安裝基礎相依套件
python -m pip install -r requirements.txt

# 啟動監控主程式
python -m troTHU.tron
```

背景服務或系統排程執行模式（關閉鍵盤監聽）：

```bash
python -m troTHU.tron run --no-input
```

### 容器化部署

專案包含標準 Dockerfile，可直接於容器或雲端平台（如 Hugging Face Spaces，連接埠 7860）運行 Web 狀態面板與監控服務：

```bash
docker build -t auto-rollcall .
docker run -d -p 7860:7860 auto-rollcall
```

## 設定指引

### 主設定檔（config.yaml）

`config.yaml` 採用高容錯的簡化鍵值格式，冒號前後有無空格均可解析，學校代碼不區分大小寫。

```yaml
now: s1120001

account:
  user: s1120001
  passwd: YourPasswordHere
  school: THU

teacher:
  user: teacher_account
  passwd: teacher_password
  school: TRONCLASS
  course:

group:
  class: A
    school: THU
    user: s1120001

operating:
  1:
    enable: true
    range:
    - 09:10 - 12:00
    - 13:20 - 17:30
  3:
    enable: true
    range:
    - 10:10 - 12:00
```

欄位說明：

- `now`：指定目前作用之學號或群組名稱。若 `account` 僅有一組帳號，此欄位可留空。
- `account`：學生帳號列表，包含 `user`（學號）、`passwd`（密碼）與 `school`（支援 THU、TKU 等）。
- `teacher`：（選用）教師輔助帳號設定，供 QR 碼全自動簽到使用。`course` 留空時自動選取首門課程。
- `group`：（選用）群組設定，可將多組帳號歸納於單一分類名稱下。
- `operating`：排程時段設定。星期代碼為 0（星期日）至 6（星期六），`range` 支援單日內定義多組監控區間。

### 進階設定檔（config.advanced.yaml）

`config.advanced.yaml` 遵循標準 YAML 規範，管理系統層級進階參數：

```yaml
time:
  timezone: Asia/Taipei

monitor:
  ignore_attendance_rate_gate: false

radar:
  strategy: empty_answer
```

### 設定管理指令

```bash
python -m troTHU.tron config show             # 檢視目前載入之完整設定
python -m troTHU.tron config doctor           # 驗證設定檔格式與欄位完整性
python -m troTHU.tron config advanced         # 開啟進階設定檔
python -m troTHU.tron config compact --write # 重整設定檔結構並自動建立備份
```

## 通知整合

支援將簽到事件與狀態推播至多種即時通訊服務，所有憑證與密鑰均透過環境變數傳遞，不寫入本地日誌。

### Discord

支援 HTTP Interactions 與 Gateway 兩種整合途徑：

```bash
python -m troTHU.tron bot discord-schema --json    # 輸出 Slash Commands 定義結構
python -m troTHU.tron bot discord-sync --dry-run   # 模擬指令同步
python -m troTHU.tron bot serve --adapter discord  # 啟動本機 Interactions 伺服器
```

### LINE Messaging API

支援 Webhook 驗證與訊息回覆，需配置以下環境變數：

```bash
LINE_CHANNEL_ACCESS_TOKEN=your_access_token
LINE_CHANNEL_SECRET=your_channel_secret
```

### Telegram

提供單向狀態推播通知：

```bash
python -m troTHU.tron account bind telegram <CHAT_ID> default
```

## 技術架構與 API 參考

TronClass 系統各校雖然前台命名不同，但底層 RESTful API 規格一致。以下列出核心流程之 API 端點供二次開發或跨校適配參考：

端點通用基礎路徑以 `{base}` 表示（例如東海大學為 `https://ilearn.thu.edu.tw`，淡江大學為 `https://iclass.tku.edu.tw`）。所有請求均須攜帶有效之會話憑證。

### 點名事件偵測

```http
GET {base}/api/radar/rollcalls?api_version=1.1.0
```

取得當前進行中之點名清單及類型標記（number、radar 或 qr）。

### 數字點名端點

```http
# 讀取伺服器點名碼
GET {base}/api/rollcall/{rollcall_id}/student_rollcalls

# 提交簽到請求
PUT {base}/api/rollcall/{rollcall_id}/answer_number_rollcall
Content-Type: application/json

{"deviceId": "<隨機值>", "numberCode": "0837"}
```

### 雷達點名端點

```http
# 預設：空資料簽到請求
PUT {base}/api/rollcall/{rollcall_id}/answer
Content-Type: application/json

{}

# 備援：帶座標之測距探測（回傳內容包含目標距離資訊）
PUT {base}/api/rollcall/{rollcall_id}/answer?api_version=1.76
```

### QR 碼動態簽到端點

```http
# 教師端建立與發起點名
POST {teacher_base}/api/course/{course_id}/rollcall
POST {teacher_base}/api/rollcall/{teacher_rollcall_id}/start-rollcall

# 教師端取得動態驗證碼
GET {teacher_base}/api/course/{course_id}/rollcall/{teacher_rollcall_id}/qr_code

# 學生端提交動態驗證碼
PUT {student_base}/api/rollcall/{student_rollcall_id}/answer_qr_rollcall
Content-Type: application/json

{"data": "<動態Token>", "deviceId": "<隨機值>"}

# 關閉臨時點名
PUT {teacher_base}/api/rollcall/{teacher_rollcall_id}/stop_qr_rollcall
```

## 專案結構

```text
auto-rollcall-thu-tronclass/
├── troTHU/
│   ├── tron.py                  # 主進入點
│   ├── runtime_context.py       # 中央狀態樞紐與模組匯出
│   ├── monitor_runtime.py       # 主監控迴圈與排程調度
│   ├── number_runtime.py        # 數字點名解析與執行
│   ├── radar_runtime.py         # 雷達點名與求解器分流
│   ├── global_radar_solver.py   # WGS84 橢球多點定位純演算法實作
│   ├── qr_runtime.py            # QR 碼提交與剪貼簿監聽
│   ├── qr_teacher_runtime.py    # 教師端動態 Token 同步流程
│   ├── providers.py             # 學校連線規格與登入流程定義
│   └── tron_http.py             # HTTP 通訊層與工作階段維持
├── config.yaml                  # 基礎排程與帳號設定檔
├── config.advanced.yaml         # 進階系統參數設定檔
├── Dockerfile                   # 容器映像檔建置定義
└── pyproject.toml               # 專案相依性與打包配置
```

## 開發與測試

專案提供完整的離線單元測試，模擬 TronClass 服務端行為以確保邏輯驗證不依賴實際校園連線：

```bash
# 語法編譯檢查
python -m py_compile troTHU/tron.py troTHU/runtime_context.py troTHU/cli_main.py

# 執行單元測試套件
python -m unittest discover -v

# 模擬發行建置檢查
python -m troTHU.tron release-build --dry-run --json
```

選用功能套件安裝：

```bash
python -m pip install -e .[packaging]   # PyInstaller 執行檔打包
python -m pip install -e .[browser]     # Playwright 瀏覽器登入支援
python -m pip install -e .[keyring]     # 系統金鑰圈密碼存儲支援
python -m pip install -e .[qr-image]    # QR 圖片解析支援
```

## 系統邊界與限制

- QR 碼全自動簽到依賴有效之教師帳號與課程開課權限；若未配置教師資訊，系統自動退回剪貼簿與手動輸入流程。
- Telegram 機器人目前僅提供單向狀態通報，未實作反向控制指令接收。
- 預編譯之 Windows 發行版本為輕量化獨立套件，未內裝 Playwright 與系統 Keyring 等選用擴充模組。

## 授權條款

本專案採用 [GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later)](./LICENSE) 授權釋出。

依據授權條款規定，凡修改本專案並公開發行，或透過網路向公眾提供衍生服務者，均須公開其對應之原始程式碼。
