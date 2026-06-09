# Hugging Face Spaces — Docker 部署設定
# HF Spaces 要求服務必須監聽 port 7860

FROM python:3.11-slim

# 設定工作目錄
WORKDIR /app

# 複製依賴定義並安裝（利用 Docker 快取層）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製所有專案程式碼
COPY troTHU/ ./troTHU/
COPY app.py .

# 建立必要的目錄（log / state 改為記憶體或暫存用）
RUN mkdir -p /tmp/tron_state /tmp/tron_log

# HF Spaces 使用非 root 用戶執行（安全要求）
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app /tmp/tron_state /tmp/tron_log
USER appuser

# HF Spaces 固定使用 port 7860
EXPOSE 7860

# 啟動命令
CMD ["python", "app.py"]
