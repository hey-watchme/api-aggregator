"""
Supabase Client Utility
========================
Supabase¥š’¡Y‹æüÆ£êÆ£â¸åüë
"""

import os
from supabase import create_client, Client
from typing import Optional


# °íüĞë	pEö	
_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Supabase¯é¤¢óÈ’EöWfÖ—

    Returns:
        Client: Supabase¯é¤¢óÈ

    Raises:
        ValueError: °ƒ	pL-šUŒfDjD4
    """
    global _supabase_client

    if _supabase_client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

        _supabase_client = create_client(url, key)
        print(f" Supabase client initialized: {url}")

    return _supabase_client
