#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aggregator API | ×íó×ÈAPI
https://api.hey-watch.me/aggregator
¹İÃÈ,šÇü¿’qWLLM(×íó×È’Y‹FastAPI¢×ê±ü·çó
"""

import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# .envÕ¡¤ën­¼
load_dotenv()

# ¨óÉİ¤óÈn¤óİüÈ
from endpoints.spot_aggregator import router as spot_router

# FastAPI¢×ê±ü·çón
app = FastAPI(
    title="Aggregator API",
    description="¹İÃÈ,šÇü¿’qWLLM(×íó×È’",
    version="1.0.0"
)

# CORS-š
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ,j°ƒgoik6PWfO`UD
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """ëüÈ¨óÉİ¤óÈ"""
    return {
        "service": "Aggregator API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "spot_aggregator": "/aggregator/spot"
        }
    }


@app.get("/health")
async def health_check():
    """Øë¹Á§Ã¯"""
    return {
        "status": "healthy",
        "service": "Aggregator API"
    }


# ¨óÉİ¤óÈn{2
app.include_router(spot_router, prefix="/aggregator", tags=["Aggregator"])


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8050))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True  # ‹zBn
    )
