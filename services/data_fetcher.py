"""
Data Fetcher Service
=====================
Fetch transcription, behavior, and emotion data from spot_features table

Key Differences from timeblock processing:
- Table: spot_features (not audio_features)
- Query key: (device_id, recorded_at) instead of (device_id, date, time_block)
"""

from typing import Optional


async def get_whisper_data(supabase_client, device_id: str, recorded_at: str) -> Optional[str]:
    """
    Fetch Whisper transcription result from spot_features

    Args:
        supabase_client: Supabase client instance
        device_id: Device ID
        recorded_at: Timestamp in ISO 8601 format (e.g., "2025-11-10T14:30:00+09:00")

    Returns:
        Transcription text or None
    """
    try:
        result = supabase_client.table('spot_features').select('vibe_transcriber_result').eq(
            'device_id', device_id
        ).eq(
            'recorded_at', recorded_at
        ).execute()

        if result.data and len(result.data) > 0:
            return result.data[0].get('vibe_transcriber_result', '')
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


async def get_emotion_data(supabase_client, device_id: str, recorded_at: str) -> Optional[list]:
    """
    Fetch emotion analysis result from spot_features
    Returns chunk-based emotion data directly from emotion_extractor_result

    Args:
        supabase_client: Supabase client instance
        device_id: Device ID
        recorded_at: Timestamp in ISO 8601 format

    Returns:
        Chunk-based emotion data or None
        Format: [{"chunk_id": 1, "start_time": 0.0, "end_time": 10.0, "primary_emotion": {...}, "emotions": [...]}, ...]
    """
    try:
        result = supabase_client.table('spot_features').select('emotion_extractor_result').eq(
            'device_id', device_id
        ).eq(
            'recorded_at', recorded_at
        ).execute()

        if result.data and len(result.data) > 0:
            extractor_result = result.data[0].get('emotion_extractor_result')
            if extractor_result and isinstance(extractor_result, list):
                return extractor_result
        return None
    except Exception as e:
        print(f"Error fetching emotion data from spot_features: {e}")
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
