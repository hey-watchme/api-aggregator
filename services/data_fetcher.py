"""
Data Fetcher Service
=====================
spot_featuresÆüÖëK‰y´½úÇü¿’Ö—Y‹µüÓ¹

Íj	ô¹:
- ÆüÖë: audio_features ’ spot_features
- ;­ü: (device_id, date, time_block) ’ (device_id, recorded_at)
"""

from typing import Optional


async def get_whisper_data(supabase_client, device_id: str, recorded_at: str) -> Optional[str]:
    """
    spot_featuresÆüÖëK‰yšn¿¤à¹¿ó×nÈéó¹¯ê×È’Ö—

    Args:
        supabase_client: Supabase¯é¤¢óÈ
        device_id: ÇÐ¤¹ID
        recorded_at: 2óåBISO 8601b: "2025-11-10T14:30:00+09:00"	

    Returns:
        ‡WwSWÆ­¹È~_oNone
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
    spot_featuresÆüÖëK‰yšn¿¤à¹¿ó×nLÕÇü¿’Ö—
    behavior_extractor_result«éàK‰YAMNetnóÿ¤ÙóÈúPœ’Ö—

    Args:
        supabase_client: Supabase¯é¤¢óÈ
        device_id: ÇÐ¤¹ID
        recorded_at: 2óåBISO 8601b	

    Returns:
        óÿ¤ÙóÈnê¹È~_oNone
    """
    try:
        result = supabase_client.table('spot_features').select('behavior_extractor_result').eq(
            'device_id', device_id
        ).eq(
            'recorded_at', recorded_at
        ).execute()

        if result.data and len(result.data) > 0:
            extractor_result = result.data[0].get('behavior_extractor_result')
            if extractor_result:
                # JSONB‹jngô¥žøhWfqH‹
                # 'events'­üLX(Y‹4oÖ—
                if isinstance(extractor_result, dict):
                    return extractor_result.get('events', [])
                return []
        return None
    except Exception as e:
        print(f"Error fetching behavior data from spot_features: {e}")
        return None


async def get_emotion_data(supabase_client, device_id: str, recorded_at: str) -> Optional[list]:
    """
    spot_featuresÆüÖëK‰yšn¿¤à¹¿ó×nÅÇü¿’Ö—
    emotion_extractor_result«éàK‰KushinadanÅy´Çü¿’Ö—

    Args:
        supabase_client: Supabase¯é¤¢óÈ
        device_id: ÇÐ¤¹ID
        recorded_at: 2óåBISO 8601b	

    Returns:
        Åy´nê¹È~_oNone
    """
    try:
        result = supabase_client.table('spot_features').select('emotion_extractor_result').eq(
            'device_id', device_id
        ).eq(
            'recorded_at', recorded_at
        ).execute()

        if result.data and len(result.data) > 0:
            extractor_result = result.data[0].get('emotion_extractor_result')
            if extractor_result:
                # JSONB‹jngô¥žøhWfqH‹
                # 'selected_features_timeline'­üLX(Y‹4oÖ—
                if isinstance(extractor_result, dict):
                    return extractor_result.get('selected_features_timeline', [])
                return []
        return None
    except Exception as e:
        print(f"Error fetching emotion data from spot_features: {e}")
        return None


async def get_spot_feature_metadata(supabase_client, device_id: str, recorded_at: str) -> Optional[dict]:
    """
    spot_featuresÆüÖëK‰local_datehlocal_time’Ö—

    Args:
        supabase_client: Supabase¯é¤¢óÈ
        device_id: ÇÐ¤¹ID
        recorded_at: 2óåBISO 8601b	

    Returns:
        {'local_date': 'YYYY-MM-DD', 'local_time': 'HH:MM:SS'}~_oNone
    """
    try:
        result = supabase_client.table('spot_features').select('local_date, local_time').eq(
            'device_id', device_id
        ).eq(
            'recorded_at', recorded_at
        ).execute()

        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    except Exception as e:
        print(f"Error fetching spot feature metadata: {e}")
        return None
