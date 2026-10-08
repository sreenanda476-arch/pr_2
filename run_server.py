"""
Hospital Emergency Capacity Prediction System
Server Runner
"""

import sys
import uvicorn
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting Hospital Emergency Capacity Prediction System on http://127.0.0.1:{port}")
    uvicorn.run("backend.app:app", host="127.0.0.1", port=port, log_level="info")
