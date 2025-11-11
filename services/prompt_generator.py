"""
Prompt Generator Service
=========================
Generate LLM analysis prompts from aggregated data

Key Differences from timeblock processing:
- Uses recorded_at (ISO 8601 timestamp) instead of time_block
- Uses device timezone to convert UTC to local time for time period calculation
- Reuses prompt format from Vibe Aggregator with spot-specific adaptations
"""

from datetime import datetime, time as time_type
from typing import Optional, Dict, List
import pytz
from services.context_builder import get_season, get_weekday_info, get_holiday_context, get_time_period
from services.subject_fetcher import generate_age_context


def generate_spot_prompt(
    transcription: Optional[str],
    behavior_data: Optional[list],
    emotion_data: Optional[list],
    recorded_at: str,
    timezone_str: str,
    subject_info: Optional[Dict] = None
) -> str:
    """
    Generate comprehensive LLM analysis prompt for spot recording

    Args:
        transcription: Transcribed text content
        behavior_data: Behavior analysis results (YAMNet)
        emotion_data: Emotion timeline data (Kushinada/OpenSMILE)
        recorded_at: UTC timestamp in ISO 8601 format
        timezone_str: Device timezone (e.g., "Asia/Tokyo")
        subject_info: Subject information

    Returns:
        Complete LLM analysis prompt string
    """
    prompt_parts = []

    # Convert UTC to local time using device timezone
    try:
        # Parse ISO 8601 timestamp
        recorded_at_dt = datetime.fromisoformat(recorded_at.replace('Z', '+00:00'))

        # Get timezone object
        timezone = pytz.timezone(timezone_str)

        # Convert to local time
        local_time_dt = recorded_at_dt.astimezone(timezone)

        # Extract components
        hour = local_time_dt.hour
        minute = local_time_dt.minute
        local_date = local_time_dt.strftime('%Y-%m-%d')
        local_time = local_time_dt.strftime('%H:%M:%S')

    except Exception as e:
        print(f"Error converting timezone: {e}")
        # Fallback to UTC
        recorded_at_dt = datetime.fromisoformat(recorded_at.replace('Z', '+00:00'))
        hour = recorded_at_dt.hour
        minute = recorded_at_dt.minute
        local_date = recorded_at_dt.strftime('%Y-%m-%d')
        local_time = recorded_at_dt.strftime('%H:%M:%S')

    # Get time period
    time_period = get_time_period(hour)

    # Get weekday and holiday information
    weekday_info = get_weekday_info(local_date)
    holiday_info = get_holiday_context(local_date)

    # Get season
    month = int(local_date.split('-')[1])
    season = get_season(month)

    # ==================== 1. Task Definition ====================
    prompt_parts.append(f"""# Spot Recording Analysis Task

Analyze the following 60-second audio recording and generate a comprehensive psychological analysis in JSON format.

# ==================== 2. Output Format & Scoring Guidelines ====================

**Output Format:**
```json
{{
  // ===== Core Information =====
  "recorded_at": "{recorded_at}",
  "summary": "2-3 sentence summary of the subject's situation and psychological state",
  "vibe_score": -36,

  // ===== Psychological Analysis =====
  "psychological_analysis": {{
    "mood_state": "neutral/positive/negative/anxious/relaxed/excited/tired",
    "mood_description": "Detailed description of the current psychological state",
    "emotion_changes": "Notable emotional transitions or stability patterns"
  }},

  // ===== Behavioral Analysis =====
  "behavioral_analysis": {{
    "detected_activities": ["conversation", "walking", "outdoor"],
    "behavior_pattern": "Overall behavioral patterns and daily activity context",
    "situation_context": "Inferred situational context and environmental factors"
  }},

  // ===== Acoustic Metrics =====
  "acoustic_metrics": {{
    // Vocal Activity
    "speech_time_ratio": 0.65,
    "average_loudness_db": -25.3,
    "loudness_range": [-45.2, -12.1],

    // Voice Quality
    "voice_stability_score": 0.82,
    "pitch_variability": "monotone/normal/expressive",
    "rhythm_regularity": 0.75,

    // Acoustic Patterns
    "dominant_patterns": [
      {{"type": "conversation", "count": 3}},
      {{"type": "silence", "frequency": "frequent"}},
      {{"type": "noise", "detected": true}}
    ]
  }},

  // ===== Key Observations =====
  "key_observations": [
    "First notable observation about the recording",
    "Second observation about timing or context",
    "Third observation about detected patterns"
  ]
}}
```

**Important Notes:**
- Output must be valid JSON (no trailing commas)
- All fields are required
- vibe_score must be integer between -100 and +100
- JSON comments (// ...) are for documentation only - do not include in output

# ==================== 3. Subject Information & Contextual Guidelines ====================

**Subject Profile:**
{generate_age_context(subject_info)}

**Analysis Guidelines:**
- If subject information is unavailable, avoid making age-specific assumptions
- Consider cultural and seasonal context when interpreting behaviors
- Time-of-day patterns: morning activities differ from evening routines
- Focus on observable patterns rather than speculative interpretations

**Special Considerations for This Time Period:**
1. First Priority: Determine if this is a conversation or solo activity
2. Second Priority: Assess environmental sounds and situational context

**Behavioral Pattern Interpretation:**
- Consistent high-confidence speech detection suggests active conversation
- Mixed activity signals may indicate environmental sounds or background noise
- Silence periods should be interpreted contextually (not always negative)

# ==================== 4. Vibe Score Calculation Guidelines ====================

**Vibe Score Range:**
- **Integer between -100 and +100 (REQUIRED)**
- Score Ranges:
  * Highly positive: 60-100
  * Positive: 20-60
  * Neutral: -20 to 20
  * Negative: -60 to -20
  * Highly negative: -100 to -60

**Scoring Factors (Subject-Specific - Age Unknown):**
- Active social interaction: +10 to +20 points (social engagement)
- Detected silence/isolation: -10 to -30 (varies by context and time of day)
- Loud noise/disturbance: -5 to -15 (environmental stress)
- Regular activity patterns: +15 to +25
- High activity diversity: +20 to +30 (varies by context)
- Low activity diversity: -20 to -30 (monotonous environment)

**Acoustic Metric Guidelines:**
- speech_time_ratio: Proportion of speech in recording (0.0-1.0) - 0.7+ is high, 0.3- is low
- average_loudness_db: Average volume in dB (typically -30 to -20 dB)
- voice_stability_score: Voice quality stability (0.0-1.0) - 0.8+ is stable, 0.5- is unstable
- pitch_variability: Voice expressiveness (monotone=flat, normal=moderate, expressive=dynamic)
- rhythm_regularity: Speech rhythm consistency (0.0-1.0) - higher means more regular patterns
""")

    # ==================== 5. Context Information ====================
    holiday_context_text = ""
    if holiday_info.get('is_holiday'):
        holiday_context_text = f"{holiday_info['holiday_name']} "
    if holiday_info.get('consecutive_context'):
        holiday_context_text += f"({holiday_info['consecutive_context']})"

    prompt_parts.append(f"""
# Temporal Context
- Country: Japan
- Season: {season}
- Date: {local_date}
- Day: {weekday_info['weekday']} ({weekday_info['day_type']}) {holiday_context_text}
- Local Time: {hour:02d}:{minute:02d} ({time_period})
- Recorded At (UTC): {recorded_at}
""")

    # Add subject information if available
    if subject_info:
        subject_parts = []
        if subject_info.get('name'):
            subject_parts.append(f"Name: {subject_info['name']}")
        if subject_info.get('age') is not None:
            subject_parts.append(f"Age: {subject_info['age']}s")
        if subject_info.get('gender'):
            subject_parts.append(f"Gender: {subject_info['gender']}")
        if subject_info.get('notes'):
            subject_parts.append(f"Notes: {subject_info['notes']}")

        prompt_parts.append("- Subject: " + ", ".join(subject_parts) + "\n")
    else:
        prompt_parts.append("- Subject: Information unavailable\n")

    # ==================== 6. Data Summary ====================
    prompt_parts.append("\n# Data Summary\n")

    # Transcription summary
    if transcription and transcription.strip():
        prompt_parts.append(f"## Transcription: Available (length: {len(transcription)} characters)")
    else:
        prompt_parts.append("## Transcription: Not available (no speech detected or transcription failed)")

    # Emotion data summary (OpenSMILE/Kushinada)
    if emotion_data and len(emotion_data) > 0:
        loudness_values = [item.get('features', {}).get('Loudness_sma3', 0) for item in emotion_data]
        jitter_values = [item.get('features', {}).get('jitterLocal_sma3nz', 0) for item in emotion_data]

        avg_loudness = sum(loudness_values) / len(loudness_values)
        max_loudness = max(loudness_values)
        min_loudness = min(loudness_values)
        avg_jitter = sum(jitter_values) / len(jitter_values)
        max_jitter = max(jitter_values)

        prompt_parts.append(f"""## Emotion Analysis (OpenSMILE) Summary:
  - Total samples: {len(emotion_data)} points
  - Average loudness: {avg_loudness:.3f} (range: {min_loudness:.3f} to {max_loudness:.3f})
  - Average jitter: {avg_jitter:.6f} (max: {max_jitter:.6f})
  - Silent samples: {jitter_values.count(0)} / {len(jitter_values)} points""")
    else:
        prompt_parts.append("## Emotion Analysis (OpenSMILE): Data not available")

    # Behavior data summary (YAMNet)
    if behavior_data:
        # Sort events by probability
        sorted_events = sorted(behavior_data, key=lambda x: x.get('prob', 0), reverse=True)

        # Categorize events by confidence level
        high_prob_events = [e for e in sorted_events if e.get('prob', 0) >= 0.7]
        mid_prob_events = [e for e in sorted_events if 0.4 <= e.get('prob', 0) < 0.7]

        speech_prob = next((e.get('prob', 0)*100 for e in sorted_events if 'Speech' in e.get('label', '')), 0)
        has_child_voice = any('Child' in e.get('label', '') or 'Baby' in e.get('label', '') for e in sorted_events[:20])
        has_noise = any('Noise' in e.get('label', '') for e in sorted_events[:10])
        activity_diversity = len([e for e in sorted_events[:20] if e.get('prob', 0) > 0.3])

        prompt_parts.append(f"""## Behavior Analysis (YAMNet) Summary:
  - Total detected events: {len(behavior_data)} unique labels
  - High confidence events (>70%): {len(high_prob_events)}
  - Medium confidence events (40-70%): {len(mid_prob_events)}
  - Speech probability: {speech_prob:.1f}%
  - Child/baby voice: {'Yes' if has_child_voice else 'No'}
  - Noise detected: {'Yes' if has_noise else 'No'}
  - Activity diversity: {activity_diversity} distinct activities""")
    else:
        prompt_parts.append("## Behavior Analysis (YAMNet): Data not available")

    # ==================== 7. Detailed Data ====================
    prompt_parts.append("\n\n# Detailed Data\n")

    # Full transcription
    if transcription and transcription.strip():
        prompt_parts.append(f"""## Full Transcription Text:
{transcription}
""")

    # Emotion timeline (OpenSMILE samples)
    if emotion_data and len(emotion_data) > 0:
        prompt_parts.append("## Emotion Timeline (OpenSMILE 1-second samples):")
        prompt_parts.append("Timestamp | Loudness | Jitter")
        prompt_parts.append("----------|----------|-------")

        for item in emotion_data[:60]:  # Limit to first 60 samples
            timestamp = item.get('timestamp', 'N/A')
            features = item.get('features', {})
            loudness = features.get('Loudness_sma3', 0)
            jitter = features.get('jitterLocal_sma3nz', 0)
            prompt_parts.append(f"{timestamp} | {loudness:.3f} | {jitter:.6f}")

    # Behavior event details
    if behavior_data:
        sorted_events = sorted(behavior_data, key=lambda x: x.get('prob', 0), reverse=True)
        prompt_parts.append("\n## Detailed Behavior Events (YAMNet Top 20):")

        # Show top 20 events
        for i, event in enumerate(sorted_events[:20], 1):
            label = event.get('label', 'Unknown')
            prob = event.get('prob', 0)
            prompt_parts.append(f"  {i}. {label}: {prob*100:.1f}%")

    return "\n".join(prompt_parts)
