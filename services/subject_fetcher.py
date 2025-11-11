"""
Subject Fetcher Service
========================
Fetch observed subject information
Reused from Vibe Aggregator codebase
"""

from typing import Optional, Dict


def generate_age_context(subject_info: Optional[Dict]) -> str:
    """Generate age and gender context string from subject information"""
    if not subject_info:
        return "Subject information unavailable"

    age = subject_info.get('age')
    gender = subject_info.get('gender', '')
    notes = subject_info.get('notes', '')

    context_parts = []

    # Age and gender context
    if age is not None:
        context_parts.append(f"{age}s {gender}")
    else:
        context_parts.append(f"Unknown age {gender}")

    # Additional notes
    if notes:
        context_parts.append(f"Notes: {notes}")

    return " / ".join(context_parts)


async def get_subject_info(supabase_client, device_id: str) -> Optional[Dict]:
    """
    Fetch subject information from device_id
    Retrieve information by joining devices and subjects tables
    """
    try:
        # First, get subject_id from devices table
        device_result = supabase_client.table('devices').select('subject_id').eq(
            'device_id', device_id
        ).execute()

        if not device_result.data or len(device_result.data) == 0:
            print(f"Device not found: {device_id}")
            return None

        subject_id = device_result.data[0].get('subject_id')
        if not subject_id:
            print(f"No subject_id for device: {device_id}")
            return None

        # Then, get subject information from subjects table
        subject_result = supabase_client.table('subjects').select(
            'subject_id', 'name', 'age', 'gender', 'notes'
        ).eq(
            'subject_id', subject_id
        ).execute()

        if subject_result.data and len(subject_result.data) > 0:
            return subject_result.data[0]

        return None
    except Exception as e:
        print(f"Error fetching subject info: {e}")
        return None
