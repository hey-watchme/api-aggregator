"""
Daily Aggregator Endpoint
==========================
Aggregate daily recording analysis data and generate LLM prompt
POST /aggregator/daily
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import json

from utils.supabase_client import get_supabase_client


router = APIRouter()


class DailyAggregatorRequest(BaseModel):
    """Daily aggregator request schema"""
    device_id: str
    local_date: str  # YYYY-MM-DD format


class DailyAggregatorResponse(BaseModel):
    """Daily aggregator response schema"""
    status: str
    device_id: str
    local_date: str
    spot_count: int
    aggregated_prompt: Optional[str] = None
    context_data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


def generate_daily_prompt(spot_results: List[Dict], local_date: str, device_id: str) -> str:
    """
    Generate daily aggregation prompt from spot_results

    Args:
        spot_results: List of spot analysis results for the day
        local_date: Local date (YYYY-MM-DD)
        device_id: Device ID

    Returns:
        LLM analysis prompt
    """
    # Build timeline of spot recordings
    timeline_entries = []

    for idx, spot in enumerate(spot_results, 1):
        recorded_at = spot.get('recorded_at', '')
        local_time = spot.get('local_time', '')
        summary = spot.get('summary', 'No summary available')
        vibe_score = spot.get('vibe_score', 0)
        behavior = spot.get('behavior', '')

        # Extract time from local_time (preferred) or recorded_at (fallback)
        try:
            if local_time:
                # Use local_time from database (already in device timezone)
                dt = datetime.fromisoformat(local_time)
                time_str = dt.strftime('%H:%M')
            else:
                # Fallback: parse recorded_at (UTC)
                dt = datetime.fromisoformat(recorded_at.replace('Z', '+00:00'))
                time_str = dt.strftime('%H:%M')
        except:
            time_str = local_time if local_time else recorded_at

        entry = f"""Recording #{idx} - {time_str}
- Summary: {summary}
- Vibe Score: {vibe_score}
- Behaviors: {behavior}"""

        timeline_entries.append(entry)

    timeline_text = "\n\n".join(timeline_entries)

    # Generate prompt
    prompt = f"""# Daily Psychological Analysis Task

## Task Overview
Analyze the following {len(spot_results)} spot recordings from {local_date} and identify significant emotional changes (burst events).

## Instructions
1. Review all spot recordings chronologically
2. Identify significant vibe score changes (≥30 points)
3. For each burst event, provide:
   - time: when it occurred (HH:MM format)
   - event: contextual insight in Japanese (why the change happened)
   - score_change: magnitude of change
4. Generate a concise daily summary in Japanese (2-3 sentences)

## Output Format (JSON)
Return ONLY a valid JSON object:
```json
{{
  "summary": "Japanese summary in 2-3 sentences describing the overall day",
  "burst_events": [
    {{
      "time": "HH:MM",
      "event": "Contextual insight in Japanese explaining the score change",
      "score_change": <integer>
    }}
  ]
}}
```

## Spot Recordings for {local_date}

{timeline_text}

---

**Important**: Return ONLY the JSON object. Do not include markdown code blocks.
"""

    return prompt


@router.post("/daily", response_model=DailyAggregatorResponse)
async def aggregate_daily(request: DailyAggregatorRequest):
    """
    Aggregate daily recording analysis data and generate LLM prompt

    Args:
        request: Device ID and local date

    Returns:
        Aggregated daily prompt and metadata

    Raises:
        HTTPException: If data retrieval or processing fails
    """
    try:
        supabase_client = get_supabase_client()

        # 1. Fetch all spot_results for the given local_date
        print(f"\n=== Daily aggregation started")
        print(f"  - Device ID: {request.device_id}")
        print(f"  - Local Date: {request.local_date}")

        result = supabase_client.table('spot_results').select('*').eq(
            'device_id', request.device_id
        ).eq(
            'local_date', request.local_date
        ).order('recorded_at').execute()

        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No spot_results found for device_id={request.device_id}, local_date={request.local_date}"
            )

        spot_results = result.data
        spot_count = len(spot_results)
        print(f"   Found {spot_count} spot recordings for {request.local_date}")

        # 2. Generate daily aggregation prompt
        aggregated_prompt = generate_daily_prompt(
            spot_results=spot_results,
            local_date=request.local_date,
            device_id=request.device_id
        )

        # 3. Build context data
        vibe_scores = [spot.get('vibe_score', 0) for spot in spot_results if spot.get('vibe_score') is not None]
        avg_vibe = sum(vibe_scores) / len(vibe_scores) if vibe_scores else 0

        context_data = {
            "spot_count": spot_count,
            "average_vibe": round(avg_vibe, 2),
            "recording_times": [spot.get('recorded_at') for spot in spot_results]
        }

        # 4. Save to daily_aggregators table
        upsert_data = {
            'device_id': request.device_id,
            'local_date': request.local_date,
            'prompt': aggregated_prompt,
            'context_data': context_data
        }

        insert_result = supabase_client.table('daily_aggregators').upsert(upsert_data).execute()

        if not insert_result.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to save aggregated prompt to daily_aggregators table"
            )

        print(f"   Daily aggregation saved to daily_aggregators table")

        # 5. Update spot_results table status (mark all spots as processed by daily aggregator)
        try:
            supabase_client.table('spot_results').update({
                'daily_aggregator_status': 'completed'
            }).eq('device_id', request.device_id).eq('local_date', request.local_date).execute()
            print(f"✅ Updated {spot_count} spot_results.daily_aggregator_status to 'completed' for {request.device_id}/{request.local_date}")
        except Exception as update_error:
            print(f"⚠️ Warning: Failed to update spot_results.daily_aggregator_status: {update_error}")
            # Continue execution even if status update fails

        return DailyAggregatorResponse(
            status="success",
            device_id=request.device_id,
            local_date=request.local_date,
            spot_count=spot_count,
            aggregated_prompt=aggregated_prompt,
            context_data=context_data,
            message=f"Daily aggregation completed successfully for {request.local_date}"
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in aggregate_daily: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
