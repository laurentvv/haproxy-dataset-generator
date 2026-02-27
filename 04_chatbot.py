#!/usr/bin/env python3
"""
04_chatbot.py - HAProxy 3.2 Documentation Chatbot
Architecture modulaire avec Gradio 6.x
"""

import sys
import io
from pathlib import Path

from app.ui.styles import CUSTOM_CSS

# Fix Windows encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.main import create_app
from app.utils.logging import setup_logging

logger = setup_logging(__name__, log_file="gradio_app.log")


def main():
    """Point d'entrée principal."""
    import argparse

    parser = argparse.ArgumentParser(
        description="HAProxy RAG Chatbot - Architecture Modulaire"
    )
    parser.add_argument("--host", default="0.0.0.0", help="Host")
    parser.add_argument("--port", default=7861, type=int, help="Port")
    parser.add_argument("--share", action="store_true", help="Share")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  🔧 HAProxy 3.2 Documentation Assistant")
    print("  Architecture Modulaire V2")
    print("=" * 60)
    print(f"  URL: http://{args.host}:{args.port}")
    print("=" * 60 + "\n")

    try:
        app = create_app()
        app.launch(
            server_name=args.host,
            server_port=args.port,
            share=args.share,
            css=CUSTOM_CSS,
        )
    except Exception as e:
        logger.critical("Critical error: %s", e)
        print(f"\n❌ {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
