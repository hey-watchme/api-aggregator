"""
Weekly Aggregator Endpoint
==========================
Aggregate weekly recording data and generate LLM prompt to pick 5 memorable events
POST /aggregator/weekly
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json

from utils.supabase_client import get_supabase_client


router = APIRouter()


class WeeklyAggregatorRequest(BaseModel):
    """Weekly aggregator request schema"""
    device_id: str
    week_start_date: str  # YYYY-MM-DD format (Monday)


class WeeklyAggregatorResponse(BaseModel):
    """Weekly aggregator response schema"""
    status: str
    device_id: str
    week_start_date: str
    week_end_date: str
    spot_count: int
    aggregated_prompt: Optional[str] = None
    context_data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


def get_week_end_date(week_start_date: str) -> str:
    """
    Calculate week end date (Sunday) from week start date (Monday)

    Args:
        week_start_date: Week start date (YYYY-MM-DD, Monday)

    Returns:
        Week end date (YYYY-MM-DD, Sunday)
    """
    start_dt = datetime.strptime(week_start_date, '%Y-%m-%d')
    end_dt = start_dt + timedelta(days=6)  # Monday + 6 days = Sunday
    return end_dt.strftime('%Y-%m-%d')


def generate_weekly_prompt(spot_features: List[Dict], week_start_date: str, week_end_date: str, device_id: str) -> str:
    """
    Generate weekly aggregation prompt from spot_features

    Args:
        spot_features: List of spot features with transcription data
        week_start_date: Week start date (YYYY-MM-DD, Monday)
        week_end_date: Week end date (YYYY-MM-DD, Sunday)
        device_id: Device ID

    Returns:
        LLM analysis prompt
    """
    # Build timeline of recordings with transcriptions
    timeline_entries = []

    for idx, spot in enumerate(spot_features, 1):
        recorded_at = spot.get('recorded_at', '')
        local_date = spot.get('local_date', '')
        local_time = spot.get('local_time', '')
        vibe_transcriber_result = spot.get('vibe_transcriber_result', {})

        # Extract transcription text
        transcription = vibe_transcriber_result.get('transcription', 'No transcription available')

        # Extract time
        try:
            if local_time:
                dt = datetime.fromisoformat(local_time)
                time_str = dt.strftime('%H:%M')
            else:
                dt = datetime.fromisoformat(recorded_at.replace('Z', '+00:00'))
                time_str = dt.strftime('%H:%M')
        except:
            time_str = local_time if local_time else recorded_at

        # Format: YYYY-MM-DD (Day) HH:MM
        try:
            date_dt = datetime.strptime(local_date, '%Y-%m-%d')
            day_of_week = ['月', '火', '水', '木', '金', '土', '日'][date_dt.weekday()]
            date_display = f"{local_date} ({day_of_week})"
        except:
            date_display = local_date

        entry = f"""Recording #{idx} - {date_display} {time_str}
- Transcription: {transcription}"""

        timeline_entries.append(entry)

    timeline_text = "\n\n".join(timeline_entries)

    # Generate prompt
    prompt = f"""# Weekly Memorable Events Selection Task

## Task Overview
Analyze the following {len(spot_features)} recordings from {week_start_date} to {week_end_date} (Monday to Sunday).
Your task is to select 5 memorable/impressive events from the week based on the transcription content.

## Instructions
1. Review all recordings chronologically
2. Select 5 memorable events that:
   - Contain interesting or notable conversations
   - Represent meaningful moments in the week
   - Help the user recall "oh yes, that happened!"
   - Show variety across the week (don't pick all from the same day if possible)
3. For each selected event, provide:
   - date: YYYY-MM-DD format
   - time: HH:MM format
   - day_of_week: 月/火/水/木/金/土/日
   - event_summary: Brief description in Japanese (1-2 sentences) explaining why this moment is memorable
   - transcription_snippet: Key part of the transcription (max 50 characters)
4. Rank the events by how memorable/impressive they are (1 = most memorable)

## Output Format (JSON)
Return ONLY a valid JSON object:
```json
{{
  "memorable_events": [
    {{
      "rank": 1,
      "date": "YYYY-MM-DD",
      "time": "HH:MM",
      "day_of_week": "月",
      "event_summary": "Japanese description explaining why this is memorable",
      "transcription_snippet": "Key part of transcription"
    }},
    {{
      "rank": 2,
      "date": "YYYY-MM-DD",
      "time": "HH:MM",
      "day_of_week": "火",
      "event_summary": "Japanese description",
      "transcription_snippet": "Key part"
    }},
    ...
  ],
  "week_summary": "Overall summary of the week in Japanese (2-3 sentences)"
}}
```

## Recordings for {week_start_date} to {week_end_date}

{timeline_text}

---

**Important**: Return ONLY the JSON object. Do not include markdown code blocks.
"""

    return prompt


@router.post("/weekly", response_model=WeeklyAggregatorResponse)
async def aggregate_weekly(request: WeeklyAggregatorRequest):
    """
    Aggregate weekly recording data and generate LLM prompt to select 5 memorable events

    Args:
        request: Device ID and week start date (Monday)

    Returns:
        Aggregated weekly prompt and metadata

    Raises:
        HTTPException: If data retrieval or processing fails
    """
    try:
        supabase_client = get_supabase_client()

        # Calculate week end date (Sunday)
        week_end_date = get_week_end_date(request.week_start_date)

        # 1. Fetch all spot_features for the week (Monday to Sunday)
        print(f"\n=== Weekly aggregation started")
        print(f"  - Device ID: {request.device_id}")
        print(f"  - Week: {request.week_start_date} to {week_end_date}")

        result = supabase_client.table('spot_features').select('*').eq(
            'device_id', request.device_id
        ).gte(
            'local_date', request.week_start_date
        ).lte(
            'local_date', week_end_date
        ).order('recorded_at').execute()

        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No spot_features found for device_id={request.device_id}, week={request.week_start_date} to {week_end_date}"
            )

        spot_features = result.data
        spot_count = len(spot_features)
        print(f"   Found {spot_count} recordings for the week")

        # 2. Generate weekly aggregation prompt
        aggregated_prompt = generate_weekly_prompt(
            spot_features=spot_features,
            week_start_date=request.week_start_date,
            week_end_date=week_end_date,
            device_id=request.device_id
        )

        # 3. Build context data
        context_data = {
            "spot_count": spot_count,
            "week_start_date": request.week_start_date,
            "week_end_date": week_end_date,
            "recording_times": [spot.get('recorded_at') for spot in spot_features]
        }

        # 4. Save to weekly_aggregators table
        upsert_data = {
            'device_id': request.device_id,
            'week_start_date': request.week_start_date,
            'prompt': aggregated_prompt,
            'context_data': context_data
        }

        insert_result = supabase_client.table('weekly_aggregators').upsert(upsert_data).execute()

        if not insert_result.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to save aggregated prompt to weekly_aggregators table"
            )

        print(f"   Weekly aggregation saved to weekly_aggregators table")

        return WeeklyAggregatorResponse(
            status="success",
            device_id=request.device_id,
            week_start_date=request.week_start_date,
            week_end_date=week_end_date,
            spot_count=spot_count,
            aggregated_prompt=aggregated_prompt,
            context_data=context_data,
            message=f"Weekly aggregation completed successfully for {request.week_start_date} to {week_end_date}"
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in aggregate_weekly: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
