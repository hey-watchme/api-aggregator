"""
Supabase Client Utility
========================
Manages Supabase client connection with singleton pattern
"""

import os
from supabase import create_client, Client
from typing import Optional


# Global singleton client instance
_supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create Supabase client instance

    Returns:
        Client: Supabase client instance

    Raises:
        ValueError: If environment variables are not set
    """
    global _supabase_client

    if _supabase_client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

        _supabase_client = create_client(url, key)
        print(f"✅ Supabase client initialized: {url}")

    return _supabase_client
