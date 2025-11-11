"""
Spot Aggregator Endpoint
=========================
π›√»,ö«¸øíqWLLM(◊ÌÛ◊»íYã®Û…›§Û»
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
    get_spot_feature_metadata
)
from services.subject_fetcher import get_subject_info
from services.prompt_generator import generate_spot_prompt


router = APIRouter()


class SpotAggregatorRequest(BaseModel):
    """π›√»,ö◊ÌÛ◊»ÍØ®π»"""
    device_id: str
    recorded_at: str  # ISO 8601b "2025-11-10T14:30:00+09:00"


class SpotAggregatorResponse(BaseModel):
    """π›√»,ö◊ÌÛ◊»Ïπ›Ûπ"""
    status: str
    device_id: str
    recorded_at: str
    local_date: Optional[str] = None
    local_time: Optional[str] = None
    aggregated_prompt: Optional[str] = None
    context_data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


@router.post("/spot", response_model=SpotAggregatorResponse)
async def aggregate_spot(request: SpotAggregatorRequest):
    """
    π›√»,ö«¸øíqWLLM(◊ÌÛ◊»í

    Args:
        request: «–§πIDh2ÛÂB

    Returns:
        q◊ÌÛ◊»h·ø«¸ø

    Raises:
        HTTPException: «¸ø÷ó®È¸~_oÊ®È¸
    """
    try:
        supabase_client = get_supabase_client()

        # 1. spot_featuresKâ·ø«¸ø÷ólocal_date, local_time	
        metadata = await get_spot_feature_metadata(
            supabase_client,
            request.device_id,
            request.recorded_at
        )

        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"No spot_features found for device_id={request.device_id}, recorded_at={request.recorded_at}"
            )

        local_date = metadata.get('local_date')
        local_time = metadata.get('local_time')

        # 2. y¥Ω˙«¸øí&÷ó
        transcription = await get_whisper_data(
            supabase_client,
            request.device_id,
            request.recorded_at
        )

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

        # 3. ≥,˛a≈1í÷ó
        subject_info = await get_subject_info(supabase_client, request.device_id)

        # 4. LLM(◊ÌÛ◊»í
        aggregated_prompt = generate_spot_prompt(
            transcription=transcription,
            behavior_data=behavior_data,
            emotion_data=emotion_data,
            recorded_at=request.recorded_at,
            local_date=local_date,
            local_time=local_time,
            subject_info=subject_info
        )

        # 5. ≥Û∆≠π»«¸øí›X(ktb
        context_data = {
            "has_transcription": transcription is not None and len(transcription.strip()) > 0,
            "has_behavior_data": behavior_data is not None and len(behavior_data) > 0,
            "has_emotion_data": emotion_data is not None and len(emotion_data) > 0,
            "has_subject_info": subject_info is not None,
            "subject_age": subject_info.get('age') if subject_info else None,
            "subject_gender": subject_info.get('gender') if subject_info else None
        }

        # 6. spot_aggregators∆¸÷Îk›X
        insert_result = supabase_client.table('spot_aggregators').upsert({
            'device_id': request.device_id,
            'recorded_at': request.recorded_at,
            'local_date': local_date,
            'local_time': local_time,
            'aggregated_prompt': aggregated_prompt,
            'context_data': context_data
        }).execute()

        if not insert_result.data:
            raise HTTPException(
                status_code=500,
                detail="Failed to save aggregated prompt to spot_aggregators table"
            )

        return SpotAggregatorResponse(
            status="success",
            device_id=request.device_id,
            recorded_at=request.recorded_at,
            local_date=local_date,
            local_time=local_time,
            aggregated_prompt=aggregated_prompt,
            context_data=context_data,
            message="Spot aggregation completed successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in aggregate_spot: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
