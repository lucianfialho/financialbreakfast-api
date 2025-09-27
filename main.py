#!/usr/bin/env python3
"""
Financial Data API - Railway Entry Point
"""

import os
from api.index import app

# Railway requires the app to be available directly
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)