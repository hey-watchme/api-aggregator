"""
Subject Fetcher Service
========================
³,þaÅ1’Ö—Y‹µüÓ¹
âXnVibe AggregatorK‰A(]n~~(ïý	
"""

from typing import Optional, Dict


def generate_age_context(subject_info: Optional[Dict]) -> str:
    """³,þanú,Å1n’Ð›zdQ’’d	"""
    if not subject_info:
        return "³,þaÅ1"

    age = subject_info.get('age')
    gender = subject_info.get('gender', '')
    notes = subject_info.get('notes', '')

    context_parts = []

    # ú,Å1n
    if age is not None:
        context_parts.append(f"{age}s {gender}")
    else:
        context_parts.append(f"tb {gender}")

    # %n™Å1’Í–
    if notes:
        context_parts.append(f"™{notes}")

    return " / ".join(context_parts)


async def get_subject_info(supabase_client, device_id: str) -> Optional[Dict]:
    """
    device_idK‰³,þaÅ1’Ö—
    devices ’ subjects ÆüÖë’PWfÅ1’Ö—
    """
    try:
        # ~Z devices ÆüÖëK‰ subject_id ’Ö—
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

        # subjects ÆüÖëK‰Å1’Ö—
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
