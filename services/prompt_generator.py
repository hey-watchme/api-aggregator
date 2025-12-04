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

    # Calculate duration from data
    has_behavior = behavior_data and len(behavior_data) > 0
    has_emotion = emotion_data and len(emotion_data) > 0
    num_blocks = max(len(behavior_data) if has_behavior else 0, len(emotion_data) if has_emotion else 0)
    duration = num_blocks * 10 if num_blocks > 0 else 60

    # ==================== 1. Task Definition ====================
    prompt_parts.append(f"""# Spot Recording Analysis Task

You are a professional counselor writing a brief session note for the client's family.

**Your audience:** Non-technical family members who want to understand what happened in this recording.
**Your tone:** Clear, simple, everyday language - as if you're talking to a concerned parent.
**Your role:**
1. **Understand what happened in THIS specific recording** (not the person's general profile)
2. **Describe the situation in plain language** that anyone can understand
3. **Avoid technical terms** (ASR, SED, SER, detection methods, time segments, data sources)

Think of this as: "After listening to this {duration}-second recording, how would you explain what happened to the client's family in simple, natural Japanese?"

Focus on: What did they say? What was happening around them? How did they seem to feel?

Your task: Analyze this recording and generate a psychological analysis in JSON format.
""")

    # ==================== 2. Output Format & Guidelines ====================
    prompt_parts.append("""
# Output Format

**Required JSON structure:**
```json
{
  "summary": "この録音で観察されたことを2-3文で記述（日本語）",
  "vibe_score": -36,
  "behavior": "検出された主要な行動パターン3つ（カンマ区切り）",
  "emotion": "最も有意な感情1-2個（カンマ区切り）"
}
```

**How to write an effective summary:**
Your summary should be like explaining to a family member - use natural, everyday language.

Focus on:
- What was said in the conversation (specific topics, complaints, requests)
- What activities were happening (cooking, playing, watching TV, eating)
- Emotional atmosphere (joyful, calm, frustrated, uncomfortable)

**Examples of good summaries (natural, everyday language):**
- "夕食の準備中。ピーマンを食べてみようとしている。足の裏が痛いと訴えている。"
- "YouTubeを見ながら笑っている。Minecraftの動画について家族に説明している。"
- "リビングで静かに過ごしている。遠くで誰かの声が聞こえるが、会話の内容ははっきりしない。"
- "宿題について話している。やりたくないと訴えている。母親と交渉中。"

**Important Notes:**
- Output must be valid JSON (no trailing commas)
- All fields are required
- summary: 2-3 sentences in Japanese describing what happened in THIS recording
- behavior: exactly 3 key behaviors separated by commas (例: 会話, 食事, 家族団らん)
- emotion: 1-2 most significant emotions from SER data (例: 喜び, 中立)
- If conversation/speech is detected in SED data, "会話" MUST be included in behavior field
- emotion field should use name_ja from SER data (喜び, 中立, 怒り, 悲しみ)
- JSON comments are for documentation only - do not include in output
""")

    # ==================== 3. Recording Context ====================
    holiday_context_text = ""
    if holiday_info.get('is_holiday'):
        holiday_context_text = f"{holiday_info['holiday_name']} "
    if holiday_info.get('consecutive_context'):
        holiday_context_text += f"({holiday_info['consecutive_context']})"

    prompt_parts.append(f"""
# Recording Context

**Temporal Information:**
- Duration: {duration} seconds
- Country: Japan
- Season: {season}
- Date: {local_date}
- Day: {weekday_info['weekday']} ({weekday_info['day_type']}) {holiday_context_text}
- Local Time: {hour:02d}:{minute:02d} ({time_period})

**Client Background (for context):**
{generate_age_context(subject_info)}
*Note: Recordings may include voices of family members or others nearby, not just the client.*
""")

    # ==================== 4. Full Transcription ====================
    prompt_parts.append("\n# Full Transcription\n")

    if transcription and transcription.strip():
        prompt_parts.append(f"{transcription}\n")
    else:
        prompt_parts.append("(No speech detected or transcription failed)\n")

    # ==================== 6. Acoustic & Emotional Timeline ====================
    prompt_parts.append("\n# Acoustic & Emotional Timeline (10-second synchronized analysis)\n")

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

    # ==================== 6. Analysis Guidelines ====================
    prompt_parts.append("""
# Analysis Process

**Step 1: Create Summary**
Based on the data above (Transcription, Acoustic events, Emotion signals), describe what happened in 2-3 sentences.

**Priority for Summary:**
1. **Conversation content (Transcription)** - PRIMARY SOURCE: What was said?
2. **Acoustic events (SED)** - CONTEXT: What activities were happening?
3. **Emotion signals (SER)** - REFERENCE: How did they seem to feel? (use cautiously)

**Step 2: Determine Vibe Score**
Based on your Summary, assign a score (-100 to +100):
- **Positive (20-100):** Joyful interactions, engaged activities, learning moments
- **Neutral (-20 to +20):** Routine activities, background conversations, passive activities
- **Negative (-100 to -20):** Discomfort, conflicts, distress

**Adjustments:**
- Time-of-day context (appropriate activities add points; late night for children subtracts points)
- Conversation engagement (active conversation adds points; silence subtracts points)
- Strong emotion signals (≥4.0) can adjust score by ±10-15 points; weak signals (<2.0) should be ignored

**Step 3: Extract Significant Emotions**
Based on the Emotion Analysis (SER) timeline:
- Identify the 1-2 emotions with the highest average scores across all time blocks
- Use the name_ja field (喜び, 中立, 怒り, 悲しみ)
- If no speech detected, use "中立" as default
- Priority: Primary emotions with score ≥ 2.0
- Example output: "喜び, 中立" or "中立"
""")

    return "\n".join(prompt_parts)
