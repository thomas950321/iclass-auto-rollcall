"""
Hugging Face Spaces 啟動入口

HF Spaces Docker 模式固定監聽 port 7860。
這個腳本把 web_gui.run_gui_server 的 port 覆寫為 7860 後啟動。

設計原則：
- 所有資料都放在記憶體（每次啟動都是乾淨狀態）
- 不強制寫入 config.yaml（Web GUI 的表單直接使用記憶體設定）
- 帳號密碼不落地，重新整理頁面後需要重新輸入
"""
import asyncio
import argparse
import os

# 確保 log / state 目錄在工作目錄可寫
os.makedirs("/app/log", exist_ok=True)
os.makedirs("/app/state", exist_ok=True)

from troTHU.web_gui import run_gui_server


def main():
    # HF Spaces 固定 port 7860；可透過環境變數覆寫（方便本機測試）
    hf_port = int(os.environ.get("PORT", "7860"))

    args = argparse.Namespace(
        host="0.0.0.0",
        port=hf_port,
        open=False,          # 容器裡不開瀏覽器
    )

    print("=" * 60)
    print(f"  🚀  Auto Rollcall Web GUI 啟動中")
    print(f"  📡  監聽位址: 0.0.0.0:{hf_port}")
    print(f"  🔒  模式: 無持久化儲存（帳號每次需重新輸入）")
    print("=" * 60)

    exit_code = asyncio.run(run_gui_server(args))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
