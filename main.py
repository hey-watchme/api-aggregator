#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aggregator API | 統合・プロンプト生成API
https://api.hey-watch.me/aggregator
3つの素材（文字起こし、音響分析、感情分析）を統合し、LLM用プロンプトを生成するFastAPIサービス
"""

import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

# エンドポイントをインポート
from endpoints.spot_aggregator import router as spot_router
from endpoints.daily_aggregator import router as daily_router
from endpoints.weekly_aggregator import router as weekly_router

# FastAPIアプリケーション初期化
app = FastAPI(
    title="Aggregator API",
    description="3つの素材を統合し、LLM用プロンプトを生成",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# エンドポイント登録
app.include_router(spot_router, prefix="/aggregator", tags=["spot"])
app.include_router(daily_router, prefix="/aggregator", tags=["daily"])
app.include_router(weekly_router, prefix="/aggregator", tags=["weekly"])

# ヘルスチェック
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "aggregator-api"}

# メイン実行
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8050))
    uvicorn.run(app, host="0.0.0.0", port=port)
