"""
Spot Aggregator Endpoint
=========================
Aggregate spot recording analysis data and generate LLM prompt
POST /aggregator/spot
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json

from utils.supabase_client import get_supabase_client
from services.data_fetcher import (
    get_whisper_data,
    get_behavior_data,
    get_emotion_data,
    get_device_timezone,
    get_local_date,
    get_local_time
)
from services.subject_fetcher import get_subject_info
from services.prompt_generator import generate_spot_prompt


router = APIRouter()


class SpotAggregatorRequest(BaseModel):
    """Spot aggregator request schema"""
    device_id: str
    recorded_at: str  # ISO 8601 format: "2025-11-10T14:30:00+09:00"


class SpotAggregatorResponse(BaseModel):
    """Spot aggregator response schema"""
    status: str
    device_id: str
    recorded_at: str
    timezone: Optional[str] = None
    aggregated_prompt: Optional[str] = None
    context_data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


@router.post("/spot", response_model=SpotAggregatorResponse)
async def aggregate_spot(request: SpotAggregatorRequest):
    """
    Aggregate spot recording analysis data and generate LLM prompt

    Args:
        request: Device ID and recorded timestamp

    Returns:
        Aggregated prompt and metadata

    Raises:
        HTTPException: If data retrieval or processing fails
    """
    try:
        supabase_client = get_supabase_client()

        # 1. Get device timezone
        timezone_str = await get_device_timezone(
            supabase_client,
            request.device_id
        )

        if not timezone_str:
            raise HTTPException(
                status_code=404,
                detail=f"No timezone found for device_id={request.device_id}"
            )

        # 2. Fetch analysis results and local_date
        whisper_data = await get_whisper_data(
            supabase_client,
            request.device_id,
            request.recorded_at
        )

        # Extract transcription text from jsonb result
        transcription = None
        if whisper_data and isinstance(whisper_data, dict):
            transcription = whisper_data.get("transcription", "")

        behavior_data = await get_behavior_data(
            supabase_client,
            request.device_id,
            request.recorded_at
        )

        emotion_data = await get_emotion_data(
            supabase_client,
            request.device_id,
            request.recorded_at
        )

        local_date = await get_local_date(
            supabase_client,
            request.device_id,
            request.recorded_at
        )

        local_time = await get_local_time(
            supabase_client,
            request.device_id,
            request.recorded_at
        )

        # 3. Get subject information
        subject_info = await get_subject_info(supabase_client, request.device_id)

        # 4. Generate LLM analysis prompt
        aggregated_prompt = generate_spot_prompt(
            transcription=transcription,
            behavior_data=behavior_data,
            emotion_data=emotion_data,
            recorded_at=request.recorded_at,
            timezone_str=timezone_str,
            subject_info=subject_info,
            local_time=local_time,
            whisper_data=whisper_data
        )

        # 5. Build context data for reference (optional metadata)
        context_data = {
            "has_transcription": transcription is not None and len(transcription.strip()) > 0,
            "has_behavior_data": behavior_data is not None and len(behavior_data) > 0,
            "has_emotion_data": emotion_data is not None and (
                (isinstance(emotion_data, dict) and emotion_data.get("total_segments", 0) > 0) or
                (isinstance(emotion_data, list) and len(emotion_data) > 0)
            ),
            "has_subject_info": subject_info is not None,
            "subject_age": subject_info.get('age') if subject_info else None,
            "subject_gender": subject_info.get('gender') if subject_info else None
        }

        # 6. Save to spot_aggregators table
        upsert_data = {
            'device_id': request.device_id,
            'recorded_at': request.recorded_at,
            'prompt': aggregated_prompt,
            'context_data': context_data
        }

        # Add local_date and local_time if available
        if local_date:
            upsert_data['local_date'] = local_date
        if local_time:
            upsert_data['local_time'] = local_time

        insert_result = supabase_client.table('spot_aggregators').upsert(upsert_data).execute()

        if not insert_result.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to save aggregated prompt to spot_aggregators table"
            )

        try:
            supabase_client.table('spot_aggregators').update({
                'aggregator_status': 'completed'
            }).eq('device_id', request.device_id).eq('recorded_at', request.recorded_at).execute()
            print(f"✅ Updated spot_aggregators.aggregator_status to 'completed' for {request.device_id}/{request.recorded_at}")
        except Exception as update_error:
            print(f"⚠️ Warning: Failed to update spot_aggregators.aggregator_status: {update_error}")

        # 7. Update spot_features table status (mark as processed by aggregator)
        try:
            supabase_client.table('spot_features').update({
                'spot_aggregator_status': 'completed'
            }).eq('device_id', request.device_id).eq('recorded_at', request.recorded_at).execute()
            print(f"✅ Updated spot_features.spot_aggregator_status to 'completed' for {request.device_id}/{request.recorded_at}")
        except Exception as update_error:
            print(f"⚠️ Warning: Failed to update spot_features.spot_aggregator_status: {update_error}")
            # Continue execution even if status update fails

        return SpotAggregatorResponse(
            status="success",
            device_id=request.device_id,
            recorded_at=request.recorded_at,
            timezone=timezone_str,
            aggregated_prompt=aggregated_prompt,
            context_data=context_data,
            message="Spot aggregation completed successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in aggregate_spot: {e}")
        try:
            supabase_client.table('spot_aggregators').update({
                'aggregator_status': 'failed'
            }).eq('device_id', request.device_id).eq('recorded_at', request.recorded_at).execute()
            print(f"✅ Updated spot_aggregators.aggregator_status to 'failed' for {request.device_id}/{request.recorded_at}")
        except Exception as update_error:
            print(f"⚠️ Warning: Failed to update spot_aggregators.aggregator_status: {update_error}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
