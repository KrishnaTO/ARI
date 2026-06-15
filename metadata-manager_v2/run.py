#!/usr/bin/env python3
"""Launcher for the ARI Metadata Manager v2.

Usage:
    python run.py [--port 8001] [--file path/to/ontology.owl]
"""
import argparse
import webbrowser
import sys
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ARI Metadata Manager v2")
    parser.add_argument("--port", type=int, default=8001, help="Port to serve on")
    parser.add_argument("--file",
                        default=str(HERE / "ontologies" / "ari_t1d.owl"),
                        help="Path to OWL ontology file")
    parser.add_argument("--no-browser", action="store_true",
                        help="Don't open browser automatically")
    args = parser.parse_args()

    os.environ["ARI_ONTOLOGY_FILE"] = args.file

    import uvicorn
    url = f"http://127.0.0.1:{args.port}"
    if not args.no_browser:
        webbrowser.open(url)
    print(f"Starting ARI Metadata Manager v2 at {url}")
    print(f"  Ontology: {args.file}")
    uvicorn.run("app.main:app", host="127.0.0.1", port=args.port, reload=False)