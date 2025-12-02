"""
Prompt Generator Service
=========================
Generate LLM analysis prompts from aggregated data with timeline synchronization

Key Features:
- Timeline-synchronized format: SED and SER data aligned by 10-second blocks
- Technology-agnostic naming: SED (Sound Event Detection), SER (Speech Emotion Recognition)
- Pattern detection: Automatic correlation between acoustic events and emotions
- Full transcription included (no timestamp segmentation)

Data Flow:
- ASR (Transcription): Full text without timestamps
- SED (Behavior): 10-second blocks with acoustic events
- SER (Emotion): 10-second chunks with emotion scores
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
    subject_info: Optional[Dict] = None,
    local_time: Optional[str] = None
) -> str:
    """
    Generate comprehensive LLM analysis prompt for spot recording

    Args:
        transcription: Transcribed text content (ASR, no timestamps)
        behavior_data: Behavior analysis results (SED, 10-second blocks)
        emotion_data: Emotion timeline data (SER, 10-second chunks)
        recorded_at: UTC timestamp in ISO 8601 format
        timezone_str: Device timezone (e.g., "Asia/Tokyo")
        subject_info: Subject information
        local_time: Local datetime string from database (e.g., "2025-11-16 12:31:01.485")

    Returns:
        Complete LLM analysis prompt with timeline-synchronized format
    """
    prompt_parts = []

    # Use local_time from database if available, otherwise convert from UTC
    try:
        if local_time:
            # Parse local_time from database (e.g., "2025-11-16 12:31:01.485")
            local_time_dt = datetime.fromisoformat(local_time)

            # Extract components
            hour = local_time_dt.hour
            minute = local_time_dt.minute
            local_date = local_time_dt.strftime('%Y-%m-%d')
            local_time_str = local_time_dt.strftime('%H:%M:%S')

            print(f"Using local_time from database: {local_time}")
        else:
            # Fallback: Convert UTC to local time using device timezone
            print(f"Warning: local_time not provided, converting from UTC")

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
            local_time_str = local_time_dt.strftime('%H:%M:%S')

    except Exception as e:
        print(f"Error processing local_time: {e}")
        # Fallback to UTC
        recorded_at_dt = datetime.fromisoformat(recorded_at.replace('Z', '+00:00'))
        hour = recorded_at_dt.hour
        minute = recorded_at_dt.minute
        local_date = recorded_at_dt.strftime('%Y-%m-%d')
        local_time_str = recorded_at_dt.strftime('%H:%M:%S')

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
  "summary": "対象者の状況と心理状態を2-3文で日本語で説明（例：朝食の時間。家族と一緒に食事をしている。）",
  "vibe_score": -36,
  "behavior": "検出された主要な行動パターン3つ（カンマ区切り、会話が含まれる場合は必ず「会話」を含める）（例：会話, 食事, 家族団らん）",

  // ===== Psychological Analysis =====
  "psychological_analysis": {{
    "mood_state": "neutral/positive/negative/anxious/relaxed/excited/tired",
    "mood_description": "現在の心理状態の詳細な説明（日本語）",
    "emotion_changes": "感情の変化や安定パターンの説明（日本語）"
  }},

  // ===== Behavioral Analysis =====
  "behavioral_analysis": {{
    "detected_activities": ["conversation", "walking", "outdoor"],
    "behavior_pattern": "全体的な行動パターンと日常活動の文脈（日本語）",
    "situation_context": "推測される状況コンテキストと環境要因（日本語）"
  }},

  // ===== Key Observations =====
  "key_observations": [
    "録音に関する重要な観察事項（日本語）",
    "タイミングや文脈に関する観察（日本語）",
    "検出されたパターンに関する観察（日本語）"
  ]
}}
```

**Important Notes:**
- Output must be valid JSON (no trailing commas)
- All fields are required
- vibe_score must be integer between -100 and +100
- **All text fields (summary, mood_description, behavior_pattern, etc.) must be in Japanese**
- **behavior field must contain exactly 3 key behaviors separated by commas (例: 会話, 食事, 家族団らん)**
- **If conversation/speech is detected in SED data, "会話" MUST be included in behavior field**
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

    # ==================== 6. Full Transcription ====================
    prompt_parts.append("\n# Full Transcription (60 seconds)\n")

    if transcription and transcription.strip():
        prompt_parts.append(f"{transcription}\n")
    else:
        prompt_parts.append("(No speech detected or transcription failed)\n")

    # ==================== 7. Acoustic & Emotional Timeline ====================
    prompt_parts.append("\n# Acoustic & Emotional Timeline (10-second synchronized analysis)\n")

    # Check data availability
    has_behavior = behavior_data and len(behavior_data) > 0
    has_emotion = emotion_data and len(emotion_data) > 0

    # Determine if emotion data should be filtered based on ASR results
    # Skip emotion analysis if no speech detected in transcription
    skip_emotion_analysis = (
        not transcription or
        not transcription.strip() or
        transcription.strip() in ["(No speech detected or transcription failed)", "発話なし"]
    )

    if not has_behavior and not has_emotion:
        prompt_parts.append("(No timeline data available)")
    else:
        # Determine number of blocks (should be 6 for 60 seconds)
        num_blocks = max(len(behavior_data) if has_behavior else 0, len(emotion_data) if has_emotion else 0)

        for i in range(num_blocks):
            start_time = i * 10
            end_time = (i + 1) * 10

            prompt_parts.append(f"## {start_time}-{end_time}秒")

            # Behavior Analysis (SED)
            if has_behavior and i < len(behavior_data):
                time_block = behavior_data[i]
                events = time_block.get('events', [])

                if events:
                    # Sort events by score
                    sorted_events = sorted(events, key=lambda x: x.get('score', 0), reverse=True)

                    prompt_parts.append("**Behavior Analysis (SED):**")
                    # Show top 3 events
                    for event in sorted_events[:3]:
                        label = event.get('label', 'Unknown')
                        score = event.get('score', 0) * 100
                        confidence = "high" if event.get('score', 0) >= 0.7 else "medium" if event.get('score', 0) >= 0.4 else "low"
                        prompt_parts.append(f"  - {label}: {score:.1f}% ({confidence} confidence)")
                else:
                    prompt_parts.append("**Behavior Analysis (SED):** No events detected")
            else:
                prompt_parts.append("**Behavior Analysis (SED):** Data not available")

            prompt_parts.append("")  # Empty line

            # Emotion Analysis (SER) - Filter based on ASR results
            if skip_emotion_analysis:
                prompt_parts.append("**Emotion Analysis (SER):** No speech detected - emotion data not applicable")
            elif has_emotion and i < len(emotion_data):
                chunk = emotion_data[i]
                primary = chunk.get('primary_emotion', {})
                emotions = chunk.get('emotions', [])

                primary_name = primary.get('name_ja', 'Unknown')
                primary_score = primary.get('score', 0)

                prompt_parts.append("**Emotion Analysis (SER):**")
                prompt_parts.append(f"  - Primary: {primary_name} (Score: {primary_score:.2f})")

                # Show all emotions
                if emotions:
                    emotion_str = ', '.join([f"{e.get('name_ja', '?')}({e.get('score', 0):.2f})" for e in emotions[:4]])
                    prompt_parts.append(f"  - All emotions: {emotion_str}")
            else:
                prompt_parts.append("**Emotion Analysis (SER):** Data not available")

            prompt_parts.append("")  # Empty line

            # Pattern interpretation - Only if emotion data is valid
            if not skip_emotion_analysis and has_behavior and i < len(behavior_data) and has_emotion and i < len(emotion_data):
                events = behavior_data[i].get('events', [])
                primary_emotion = emotion_data[i].get('primary_emotion', {}).get('name_ja', '')

                # Simple pattern detection
                has_speech = any('Speech' in e.get('label', '') for e in events)
                has_laughter = any('Laughter' in e.get('label', '') or '笑い' in e.get('label', '') for e in events)
                has_crying = any('Crying' in e.get('label', '') or '泣' in e.get('label', '') for e in events)

                pattern = "**Pattern:** "
                if has_laughter and '喜び' in primary_emotion:
                    pattern += "笑い声と喜びの感情が一致 → 高信頼性のポジティブ状態"
                elif has_crying and ('悲しみ' in primary_emotion or '怒り' in primary_emotion):
                    pattern += "泣き声とネガティブ感情が一致 → 高信頼性の苦痛状態"
                elif has_speech:
                    pattern += f"会話中、{primary_emotion}の感情"
                else:
                    pattern += f"{primary_emotion}の感情状態"

                prompt_parts.append(pattern)
            elif skip_emotion_analysis and has_behavior and i < len(behavior_data):
                # Pattern for behavior-only (no emotion)
                events = behavior_data[i].get('events', [])
                if events:
                    top_event = events[0].get('label', '').split('/')[0].strip()
                    prompt_parts.append(f"**Pattern:** {top_event}の状態")

            prompt_parts.append("\n---\n")  # Separator between blocks

    # ==================== 8. Overall Summary ====================
    prompt_parts.append("\n# Overall Summary\n")

    # Duration
    duration = num_blocks * 10 if (has_behavior or has_emotion) else 60
    prompt_parts.append(f"- **Duration:** {duration} seconds")

    # Speech activity summary
    if has_behavior:
        all_speech_scores = []
        for time_block in behavior_data:
            for event in time_block.get('events', []):
                if 'Speech' in event.get('label', ''):
                    all_speech_scores.append(event.get('score', 0))

        if all_speech_scores:
            avg_speech = sum(all_speech_scores) / len(all_speech_scores) * 100
            max_speech = max(all_speech_scores) * 100
            max_time = 0
            for i, time_block in enumerate(behavior_data):
                for event in time_block.get('events', []):
                    if 'Speech' in event.get('label', '') and event.get('score', 0) == max(all_speech_scores):
                        max_time = i * 10
                        break

            prompt_parts.append(f"- **Speech Activity:** Average {avg_speech:.1f}%, Peak {max_speech:.1f}% at {max_time}-{max_time+10}s")

        # Child voice detection
        has_child = any(any('Child' in e.get('label', '') or 'Baby' in e.get('label', '') for e in tb.get('events', [])) for tb in behavior_data)
        prompt_parts.append(f"- **Child Voice:** {'Detected' if has_child else 'Not detected'}")

    # Emotion trend summary - Only if speech detected
    if has_emotion and not skip_emotion_analysis:
        primary_emotions = [chunk.get('primary_emotion', {}).get('name_ja', 'Unknown') for chunk in emotion_data]
        emotion_scores = [chunk.get('primary_emotion', {}).get('score', 0) for chunk in emotion_data]

        avg_score = sum(emotion_scores) / len(emotion_scores)
        max_score = max(emotion_scores)
        min_score = min(emotion_scores)
        max_time = emotion_scores.index(max_score) * 10
        dominant = max(set(primary_emotions), key=primary_emotions.count)

        prompt_parts.append(f"- **Emotion Trend:** {dominant} (dominant), Range: {min_score:.2f}-{max_score:.2f}, Peak: {max_time}s")
        prompt_parts.append(f"- **Emotion Timeline:** {' → '.join(primary_emotions)}")
    elif has_emotion and skip_emotion_analysis:
        prompt_parts.append(f"- **Emotion Trend:** No speech detected - emotion data skipped for all {len(emotion_data)} segments")

    # Key patterns - Only if emotion data is valid
    if has_behavior and has_emotion and not skip_emotion_analysis:
        prompt_parts.append("- **Key Patterns:**")

        # Find peak emotion and corresponding behavior
        emotion_scores = [chunk.get('primary_emotion', {}).get('score', 0) for chunk in emotion_data]
        if emotion_scores:
            peak_idx = emotion_scores.index(max(emotion_scores))
            peak_emotion = emotion_data[peak_idx].get('primary_emotion', {}).get('name_ja', 'Unknown')
            peak_events = behavior_data[peak_idx].get('events', []) if peak_idx < len(behavior_data) else []
            peak_event_labels = [e.get('label', '').split('/')[0].strip() for e in peak_events[:2]]

            prompt_parts.append(f"  - Emotional peak at {peak_idx*10}s ({peak_emotion}: {max(emotion_scores):.2f})")
            if peak_event_labels:
                prompt_parts.append(f"  - Concurrent behaviors: {', '.join(peak_event_labels)}")

    return "\n".join(prompt_parts)
