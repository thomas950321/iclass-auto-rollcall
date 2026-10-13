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
import sys

# Windows 終端機編碼相容性處理
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 確保 log / state 目錄在工作目錄可寫
os.makedirs("log", exist_ok=True)
os.makedirs("state", exist_ok=True)

from troTHU.web_gui import run_gui_server


def main():
    parser = argparse.ArgumentParser(description="Auto Rollcall Web GUI")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "7860")), help="服務監聽通訊埠")
    parser.add_argument("--host", default="0.0.0.0", help="監聽位址")
    parser.add_argument("--open", action="store_true", default=not os.path.exists("/.dockerenv"), help="自動於預設瀏覽器開啟")
    parser.add_argument("--no-open", dest="open", action="store_false", help="不開啟瀏覽器")
    cli_args = parser.parse_args()

    args = argparse.Namespace(
        host=cli_args.host,
        port=cli_args.port,
        open=cli_args.open,
    )

    print("=" * 60)
    print("  [Auto Rollcall Web GUI 啟動中]")
    print(f"  監聽位址: {args.host}:{args.port}")
    print("  模式: 無持久化儲存（帳號每次需重新輸入）")
    if args.open:
        print(f"  即將於瀏覽器開啟: http://127.0.0.1:{args.port}")
    print("=" * 60)

    exit_code = asyncio.run(run_gui_server(args))
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
