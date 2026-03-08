"""
Data Fetcher Service
=====================
Fetch transcription, behavior, and emotion data from spot_features table

Key Differences from timeblock processing:
- Table: spot_features (not audio_features)
- Query key: (device_id, recorded_at) instead of (device_id, date, time_block)
"""

from typing import Optional


async def get_whisper_data(supabase_client, device_id: str, recorded_at: str) -> Optional[dict]:
    """
    Fetch transcription result from spot_features (jsonb column).

    Args:
        supabase_client: Supabase client instance
        device_id: Device ID
        recorded_at: Timestamp in ISO 8601 format

    Returns:
        dict with transcription data or None
        Format: {"transcription": "...", "words": [...], "speaker_count": N, ...}
    """
    try:
        result = supabase_client.table('spot_features').select('vibe_transcriber_result').eq(
            'device_id', device_id
        ).eq(
            'recorded_at', recorded_at
        ).execute()

        if result.data and len(result.data) > 0:
            vibe_result = result.data[0].get('vibe_transcriber_result')
            if vibe_result is None:
                return None
            # Handle legacy text format (pre-migration data)
            if isinstance(vibe_result, str):
                return {"transcription": vibe_result}
            return vibe_result
        return None
    except Exception as e:
        print(f"Error fetching transcriber data: {e}")
        return None


async def get_behavior_data(supabase_client, device_id: str, recorded_at: str) -> Optional[list]:
    """
    Fetch behavior analysis result from spot_features
    Returns time-based event list directly from behavior_extractor_result

    Args:
        supabase_client: Supabase client instance
        device_id: Device ID
        recorded_at: Timestamp in ISO 8601 format

    Returns:
        List of time-based behavior events or None
        Format: [{"time": 0.0, "events": [{"label": "Speech", "score": 0.76}, ...]}, ...]
    """
    try:
        result = supabase_client.table('spot_features').select('behavior_extractor_result').eq(
            'device_id', device_id
        ).eq(
            'recorded_at', recorded_at
        ).execute()

        if result.data and len(result.data) > 0:
            extractor_result = result.data[0].get('behavior_extractor_result')
            if extractor_result and isinstance(extractor_result, list):
                return extractor_result
        return None
    except Exception as e:
        print(f"Error fetching behavior data from spot_features: {e}")
        return None


async def get_emotion_data(supabase_client, device_id: str, recorded_at: str):
    """
    Fetch Hume v3 emotion analysis result from spot_features.

    Returns:
        dict (Hume v3 format with provider="hume") or None
    """
    try:
        result = supabase_client.table('spot_features').select(
            'emotion_features_result_hume'
        ).eq(
            'device_id', device_id
        ).eq(
            'recorded_at', recorded_at
        ).execute()

        if result.data and len(result.data) > 0:
            hume_result = result.data[0].get('emotion_features_result_hume')
            if hume_result and isinstance(hume_result, dict):
                return hume_result

        return None
    except Exception as e:
        print(f"Error fetching emotion data from spot_features: {e}")
        return None


async def get_local_date(supabase_client, device_id: str, recorded_at: str) -> Optional[str]:
    """
    Fetch local_date from spot_features

    Args:
        supabase_client: Supabase client instance
        device_id: Device ID
        recorded_at: Timestamp in ISO 8601 format

    Returns:
        Local date string (YYYY-MM-DD) or None
    """
    try:
        result = supabase_client.table('spot_features').select('local_date').eq(
            'device_id', device_id
        ).eq(
            'recorded_at', recorded_at
        ).execute()

        if result.data and len(result.data) > 0:
            return result.data[0].get('local_date')
        return None
    except Exception as e:
        print(f"Error fetching local_date from spot_features: {e}")
        return None


async def get_local_time(supabase_client, device_id: str, recorded_at: str) -> Optional[str]:
    """
    Fetch local_time from spot_features

    Args:
        supabase_client: Supabase client instance
        device_id: Device ID
        recorded_at: Timestamp in ISO 8601 format

    Returns:
        Local time string (YYYY-MM-DD HH:MM:SS) or None
    """
    try:
        result = supabase_client.table('spot_features').select('local_time').eq(
            'device_id', device_id
        ).eq(
            'recorded_at', recorded_at
        ).execute()

        if result.data and len(result.data) > 0:
            return result.data[0].get('local_time')
        return None
    except Exception as e:
        print(f"Error fetching local_time from spot_features: {e}")
        return None


async def get_device_timezone(supabase_client, device_id: str) -> Optional[str]:
    """
    Fetch timezone from devices table

    Args:
        supabase_client: Supabase client instance
        device_id: Device ID

    Returns:
        Timezone string (e.g., "Asia/Tokyo") or None
    """
    try:
        result = supabase_client.table('devices').select('timezone').eq(
            'device_id', device_id
        ).execute()

        if result.data and len(result.data) > 0:
            return result.data[0].get('timezone')
        return None
    except Exception as e:
        print(f"Error fetching device timezone: {e}")
        return None
