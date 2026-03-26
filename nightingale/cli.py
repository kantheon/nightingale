"""Nightingale CLI — launch the clinical documentation interface."""

import argparse


def main():
    parser = argparse.ArgumentParser(
        description="Nightingale: Local clinical documentation assistant"
    )
    parser.add_argument(
        "--port", type=int, default=3000,
        help="Port for the web interface (default: 3000)"
    )
    parser.add_argument(
        "--model", type=str, default=None,
        help="Kandiga model to use (default: Qwen3.5-35B-A3B-4bit)"
    )
    args = parser.parse_args()

    import uvicorn

    print(f"""
    ╔══════════════════════════════════════════════════╗
    ║              NIGHTINGALE v0.1.0                  ║
    ║    Local Clinical Documentation Assistant        ║
    ║                                                  ║
    ║    Open in browser: http://localhost:{args.port:<5}       ║
    ║                                                  ║
    ║    All data stays on this device.                ║
    ║    No internet connection required.              ║
    ╚══════════════════════════════════════════════════╝
    """)

    uvicorn.run(
        "nightingale.server:app",
        host="127.0.0.1",
        port=args.port,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
