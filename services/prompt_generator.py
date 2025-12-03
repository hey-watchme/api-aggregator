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
  "behavior": "検出された主要な行動パターン3つ（カンマ区切り）"
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

**What NOT to do (avoid these patterns):**
- ❌ "ASRでは発話が検出されなかった" → ✅ "会話の内容は記録されていない" or "何を話しているかは不明"
- ❌ "SEDでは0-10秒に音声信号が報告" → ✅ "背景に声が聞こえる" or "遠くで話し声がする"
- ❌ "SERデータによると喜びの感情" → ✅ "楽しそうな様子" or "嬉しそうに見える"
- ❌ "時間セグメント(0-10s, 10-20s)を明記" → ✅ Just describe what happened overall

**Remember:** You're explaining to someone who doesn't know how the recording system works. Use natural Japanese that anyone can understand.

**Important Notes:**
- Output must be valid JSON (no trailing commas)
- All fields are required
- vibe_score must be integer between -100 and +100
- summary: 2-3 sentences in Japanese describing what happened in THIS recording
- behavior: exactly 3 key behaviors separated by commas (例: 会話, 食事, 家族団らん)
- If conversation/speech is detected in SED data, "会話" MUST be included in behavior field
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

**Device Context:**
- Recording device is stationary, placed in the living room
- Conversations may include family members (not just the client)

*Note: This background helps you understand the context, but your summary should focus on what happened in THIS recording.*

**Analysis Guidelines:**
- Consider cultural and seasonal context when interpreting behaviors
- Time-of-day patterns: morning activities differ from evening routines
- Focus on observable patterns rather than speculative interpretations
- First Priority: Determine if this is a conversation or solo activity
- Second Priority: Assess environmental sounds and situational context
- Consistent high-confidence speech detection suggests active conversation
- Mixed activity signals may indicate environmental sounds or background noise
- Silence periods should be interpreted contextually (not always negative)

# ==================== 4. Vibe Score Calculation Guidelines ====================

**Core Principle:**
Base your Vibe Score on the **Summary** and **Behavior** you generated, which should integrate:
1. **Conversation content (ASR)** - PRIMARY SOURCE (最優先)
2. **Acoustic events (SED)** - RELIABLE CONTEXT (会話を補完・状況理解)
3. **Emotion scores (SER)** - MINOR ADJUSTMENT ONLY (精度低い・参考程度)

**Vibe Score Range:**
- **Integer between -100 and +100 (REQUIRED)**
- Score Ranges:
  * Highly positive: 60-100
  * Positive: 20-60
  * Neutral: -20 to 20
  * Negative: -60 to -20
  * Highly negative: -100 to -60

---

## Scoring Process

### Step 1: Generate Summary Using ASR + SED

**Summary should reflect:**
- What is being said (conversation content from ASR)
- What is happening (activities detected by SED)
- Overall situation combining both sources

**SED enhances understanding:**
- Speech → confirms active conversation
- Sizzle, Frying → reveals cooking activity (may not be mentioned in words)
- Music, TV → background entertainment
- Laughter → positive atmosphere (even if not captured in transcription)
- Crying, Screaming → distress (even if words are unclear)

**Example:**
- ASR: "足の裏が痛い。ピーマン食べてみる。"
- SED: Sizzle, Frying, Speech
- Summary: "料理中。足が痛いと訴えているが、新しい野菜に挑戦している。家族との会話が続いている。"

---

### Step 2: Determine Base Score from Summary (-60 to +60)

Read your Summary and ask: "What is the overall situation?"

**Highly Positive (40-60):**
- Joyful family interactions (楽しい遊び、笑い声、ポジティブな会話)
- Learning/discovery moments (新しい挑戦、成功体験、褒められる)
- Active positive engagement (協力して料理、一緒にゲーム)

**Positive (20-40):**
- Regular positive activities (日常的な会話、食事、遊び)
- Calm family time (穏やかな団らん、一緒にTV視聴)
- Engaged activities (YouTube視聴中のコメント、料理の手伝い)

**Neutral (-20 to +20):**
- Routine activities without emotional tone (移動中、静かな時間)
- Background conversations (内容不明瞭、雑談)
- Passive activities (TV/音楽を聴いているだけ)

**Negative (-40 to -20):**
- Minor discomfort or complaints (痛い、疲れた、イヤだ)
- Mild conflicts (注意される、小言を言われる)
- Frustration (うまくいかない、飽きた)

**Highly Negative (-60 to -40):**
- Intense distress (激しく泣く、パニック、怒鳴る)
- Serious conflicts (大きな喧嘩、強く叱られる)
- Clear suffering (強い痛み、恐怖、助けを求める)

---

### Step 3: Contextual Adjustments (-20 to +20)

**A. Time-of-Day Context (-15 to +10)**

Age-appropriate timing matters:
- **Appropriate activity for time**: 0 to +10
  * Morning (6:00-9:00): Breakfast, getting ready → +5
  * Daytime (9:00-17:00): Active play, learning → +10
  * Evening (17:00-20:00): Dinner, family time → +5
  * Night (20:00-22:00): Calm activities, bedtime routine → 0

- **Inappropriate timing** (especially for young children): -10 to -15
  * Late night (22:00-6:00): Should be sleeping → -10 to -15
  * Missing meal times: Unusual absence → -5

**B. Conversation Engagement (-15 to +10)**

Based on both ASR and SED:
- **Active conversation** (ASR content + Speech 0.5+): +5 to +10
  * Rich conversation content + high Speech confidence → +10
  * Brief conversation + medium Speech confidence → +5

- **Activity sounds without speech** (SED only): 0 to +5
  * Cooking, playing, movement sounds → +5 (engaged in activity)
  * TV, Music only → 0 (passive consumption)

- **Complete silence** (no ASR, no SED): -10 to -15
  * Likely absent or outside → -15
  * Possible nap time (if appropriate hour) → -5

---

### Step 4: Emotion Data (SER) - Fine-Tuning Only (-10 to +10)

**⚠️ Use with caution - SER has high false positive rate**

Only apply if emotion data aligns with Summary:
- **Emotion supports Summary**: -10 to +10
  * Summary is positive AND Joy score is high (3.0+) → +5 to +10
  * Summary is negative AND Anger/Sadness score is high → -5 to -10

- **Emotion contradicts Summary**: IGNORE emotion data
  * Example: Fun conversation but Anger score is high → Trust Summary, ignore SER
  * Example: Complaint in words but Joy score is high → Trust ASR, ignore SER

**Default behavior**: If uncertain, do NOT use SER data at all (0 adjustment)

---

## Key Reminders

1. **ASR (conversation) is your primary source** - understand what is being said
2. **SED (acoustic events) enriches context** - reveals activities not in words
3. **SER (emotion) is secondary** - only use if it clearly supports Summary
4. **Trust your Summary over raw data** - if they conflict, trust your interpretation
""")

    # ==================== 5. Full Transcription ====================
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

    return "\n".join(prompt_parts)
