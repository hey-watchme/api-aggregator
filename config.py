"""
Configuration Module
====================
°ƒ	ph-š’¡
"""

import os
from dotenv import load_dotenv

# .envÕ¡¤ë’­¼
load_dotenv()

# Supabase-š
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# ¢×ê±ü·çó-š
PORT = int(os.getenv("PORT", 8050))
HOST = os.getenv("HOST", "0.0.0.0")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

# í°ìÙë
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
