"""
Prompt Generator Service
=========================
Generate LLM analysis prompts from aggregated data with timeline synchronization

Key Features:
- Timeline-synchronized format: SED and SER data aligned by 10-second blocks
- Technology-agnostic naming: SED (Sound Event Detection), SER (Speech Emotion Recognition)
- Hume AI v3 support: 48-emotion prosody/burst/language analysis
- Full transcription included (no timestamp segmentation)

Data Flow:
- ASR (Transcription): Full text without timestamps
- SED (Behavior): 1-second events from behavior extractor
- SER (Emotion): Hume v3 (48 emotions, utterance-based) or legacy (4 emotions, chunk-based)
"""

from datetime import datetime, time as time_type
from typing import Optional, Dict, List, Any, Union
import pytz
from services.context_builder import get_season, get_weekday_info, get_holiday_context, get_time_period
from services.subject_fetcher import generate_age_context


HUME_EMOTION_JA = {
    "Admiration": "称賛",
    "Adoration": "愛慕",
    "Aesthetic Appreciation": "美的感動",
    "Amusement": "楽しさ",
    "Anger": "怒り",
    "Annoyance": "苛立ち",
    "Anxiety": "不安",
    "Awe": "畏敬",
    "Awkwardness": "気まずさ",
    "Boredom": "退屈",
    "Calmness": "穏やかさ",
    "Concentration": "集中",
    "Confusion": "困惑",
    "Contemplation": "熟考",
    "Contempt": "軽蔑",
    "Contentment": "満足",
    "Craving": "渇望",
    "Desire": "欲求",
    "Determination": "決意",
    "Disappointment": "失望",
    "Disapproval": "不承認",
    "Disgust": "嫌悪",
    "Distress": "苦悩",
    "Doubt": "疑念",
    "Ecstasy": "恍惚",
    "Embarrassment": "恥ずかしさ",
    "Empathic Pain": "共感的苦痛",
    "Enthusiasm": "熱意",
    "Entrancement": "魅了",
    "Envy": "嫉妬",
    "Excitement": "興奮",
    "Fear": "恐怖",
    "Gratitude": "感謝",
    "Guilt": "罪悪感",
    "Horror": "戦慄",
    "Interest": "関心",
    "Joy": "喜び",
    "Love": "愛",
    "Nostalgia": "郷愁",
    "Pain": "痛み",
    "Pride": "誇り",
    "Realization": "気づき",
    "Relief": "安堵",
    "Romance": "ロマンス",
    "Sadness": "悲しみ",
    "Sarcasm": "皮肉",
    "Satisfaction": "満足感",
    "Shame": "羞恥",
    "Surprise (negative)": "驚き(ネガティブ)",
    "Surprise (positive)": "驚き(ポジティブ)",
    "Sympathy": "同情",
    "Tiredness": "疲労",
    "Triumph": "勝利感",
}


def _is_hume_format(emotion_data) -> bool:
    """Check if emotion data is Hume v3 format (dict with provider='hume')"""
    return isinstance(emotion_data, dict) and emotion_data.get("provider") == "hume"


def _top_emotions(emotions_dict: Dict[str, float], n: int = 3) -> List[tuple]:
    """Extract top N emotions by score from a {name: score} dict"""
    sorted_emotions = sorted(emotions_dict.items(), key=lambda x: x[1], reverse=True)
    return sorted_emotions[:n]


def _emotion_ja(name: str) -> str:
    """Translate Hume emotion name to Japanese"""
    return HUME_EMOTION_JA.get(name, name)


def _format_top_emotions(emotions_dict: Dict[str, float], n: int = 3) -> str:
    """Format top N emotions as 'JA名(score)' string"""
    top = _top_emotions(emotions_dict, n)
    return ", ".join(f"{_emotion_ja(name)}({score:.2f})" for name, score in top)


def _format_hume_emotion_section(emotion_data: Dict[str, Any], skip_emotion: bool) -> str:
    """
    Format Hume v3 emotion data as a prompt section.
    Returns a string with speech prosody, vocal burst, and language analysis.
    """
    if skip_emotion:
        return "\n# emotion_extractor_result\n\nNo speech detected - emotion data not applicable\n"

    parts = []
    parts.append("\n# emotion_extractor_result (Hume AI - 48 Emotion Analysis)\n")

    # --- Speech Prosody ---
    prosody = emotion_data.get("speech_prosody", {})
    prosody_segments = prosody.get("segments", [])

    if prosody_segments:
        parts.append("## Voice Tone Emotion (speech_prosody)")
        for seg in prosody_segments:
            time_info = seg.get("time", {})
            begin = time_info.get("begin", 0)
            end = time_info.get("end", 0)
            text = seg.get("text", "")
            emotions = seg.get("emotions", {})
            dominant = seg.get("dominant_emotion", {})

            text_preview = text[:30] + "..." if len(text) > 30 else text
            top_str = _format_top_emotions(emotions, 3)
            dominant_ja = _emotion_ja(dominant.get("name", ""))

            parts.append(
                f"[{begin:.1f}-{end:.1f}s] \"{text_preview}\"  "
                f"Dominant: {dominant_ja}({dominant.get('score', 0):.2f})  "
                f"Top: {top_str}"
            )
        parts.append("")

    # --- Vocal Burst ---
    burst = emotion_data.get("vocal_burst", {})
    burst_segments = burst.get("segments", [])

    if burst_segments:
        parts.append("## Non-speech Vocal Emotion (vocal_burst)")
        for seg in burst_segments:
            time_info = seg.get("time", {})
            begin = time_info.get("begin", 0)
            end = time_info.get("end", 0)
            emotions = seg.get("emotions", {})
            dominant = seg.get("dominant_emotion", {})

            top_str = _format_top_emotions(emotions, 3)
            dominant_ja = _emotion_ja(dominant.get("name", ""))

            parts.append(
                f"[{begin:.1f}-{end:.1f}s]  "
                f"Dominant: {dominant_ja}({dominant.get('score', 0):.2f})  "
                f"Top: {top_str}"
            )
        parts.append("")

    # --- Language ---
    language = emotion_data.get("language", {})
    lang_segments = language.get("segments", [])

    if lang_segments:
        parts.append("## Text-based Emotion (language)")
        for seg in lang_segments:
            emotions = seg.get("emotions", {})
            dominant = seg.get("dominant_emotion", {})

            top_str = _format_top_emotions(emotions, 5)
            dominant_ja = _emotion_ja(dominant.get("name", ""))

            parts.append(
                f"Dominant: {dominant_ja}({dominant.get('score', 0):.2f})  "
                f"Top: {top_str}"
            )
        parts.append("")

    if not prosody_segments and not burst_segments and not lang_segments:
        parts.append("(No emotion segments detected)")

    return "\n".join(parts)


def _build_unified_timeline(
    whisper_data: Optional[Dict],
    behavior_data: Optional[list],
    emotion_data: Optional[Union[list, Dict]],
    block_seconds: int = 5
) -> str:
    """
    Build a unified timeline combining ASR, SED, and SER data
    aligned by fixed-duration time blocks.
    """
    has_words = (whisper_data and isinstance(whisper_data, dict)
                 and whisper_data.get("words"))
    has_behavior = behavior_data and len(behavior_data) > 0
    hume_mode = _is_hume_format(emotion_data) if emotion_data else False

    # Determine total duration from available data
    max_time = 0
    if has_words:
        for w in whisper_data["words"]:
            et = w.get("end_time", 0)
            if et > max_time:
                max_time = et
    if has_behavior:
        last_t = behavior_data[-1].get("time", 0)
        if last_t + 1 > max_time:
            max_time = last_t + 1
    if hume_mode:
        for seg in emotion_data.get("speech_prosody", {}).get("segments", []):
            et = seg.get("time", {}).get("end", 0)
            if et > max_time:
                max_time = et

    if max_time == 0:
        max_time = 60

    num_blocks = int(max_time // block_seconds) + 1
    parts = []
    parts.append(f"\n# Unified Analysis Timeline ({block_seconds}s blocks)\n")

    for b in range(num_blocks):
        t_start = b * block_seconds
        t_end = (b + 1) * block_seconds
        block_parts = []

        # --- ASR: words in this block ---
        if has_words:
            speakers_in_block = {}
            for w in whisper_data["words"]:
                wt = w.get("start_time", 0)
                if t_start <= wt < t_end and w.get("type") == "word":
                    spk = w.get("speaker", "?")
                    if spk not in speakers_in_block:
                        speakers_in_block[spk] = []
                    speakers_in_block[spk].append(w.get("content", ""))
            # Also pick up punctuation that follows words in this block
            for w in whisper_data["words"]:
                wt = w.get("start_time", 0)
                if t_start <= wt < t_end and w.get("type") == "punctuation":
                    spk = w.get("speaker", "?")
                    if spk in speakers_in_block and speakers_in_block[spk]:
                        speakers_in_block[spk][-1] += w.get("content", "")

            if speakers_in_block:
                for spk, tokens in speakers_in_block.items():
                    text = "".join(tokens)
                    block_parts.append(f"  ASR [{spk}]: \"{text}\"")

        # --- SED: behavior events in this block ---
        if has_behavior:
            block_events = {}
            for entry in behavior_data:
                t = entry.get("time", 0)
                if t_start <= t < t_end:
                    for ev in entry.get("events", []):
                        label = ev.get("label", "Unknown")
                        score = ev.get("score", 0)
                        if label in block_events:
                            block_events[label] = max(block_events[label], score)
                        else:
                            block_events[label] = score

            if block_events:
                sorted_ev = sorted(block_events.items(), key=lambda x: x[1], reverse=True)[:3]
                ev_str = ", ".join(f"{l}({s*100:.0f}%)" for l, s in sorted_ev)
                block_parts.append(f"  SED: {ev_str}")

        # --- SER: emotion segments overlapping this block ---
        if hume_mode:
            prosody_segs = emotion_data.get("speech_prosody", {}).get("segments", [])
            for seg in prosody_segs:
                seg_begin = seg.get("time", {}).get("begin", 0)
                seg_end = seg.get("time", {}).get("end", 0)
                if seg_begin < t_end and seg_end > t_start:
                    dominant = seg.get("dominant_emotion", {})
                    d_name = _emotion_ja(dominant.get("name", ""))
                    d_score = dominant.get("score", 0)
                    emotions = seg.get("emotions", {})
                    top3 = _top_emotions(emotions, 3)
                    top_str = ", ".join(
                        f"{_emotion_ja(n)}({s:.2f})" for n, s in top3
                    )
                    block_parts.append(
                        f"  SER [{seg_begin:.1f}-{seg_end:.1f}s]: "
                        f"{d_name}({d_score:.2f}) | {top_str}"
                    )

            burst_segs = emotion_data.get("vocal_burst", {}).get("segments", [])
            for seg in burst_segs:
                seg_begin = seg.get("time", {}).get("begin", 0)
                seg_end = seg.get("time", {}).get("end", 0)
                if seg_begin < t_end and seg_end > t_start:
                    dominant = seg.get("dominant_emotion", {})
                    d_name = _emotion_ja(dominant.get("name", ""))
                    d_score = dominant.get("score", 0)
                    block_parts.append(
                        f"  SER(burst) [{seg_begin:.1f}-{seg_end:.1f}s]: "
                        f"{d_name}({d_score:.2f})"
                    )

        if block_parts:
            parts.append(f"## {t_start}-{t_end}s")
            parts.extend(block_parts)
            parts.append("")

    # --- Language-level emotion (full-text, not time-based) ---
    if hume_mode:
        lang_segs = emotion_data.get("language", {}).get("segments", [])
        if lang_segs:
            parts.append("## Overall Text Emotion (language analysis)")
            seg = lang_segs[0]
            dominant = seg.get("dominant_emotion", {})
            d_name = _emotion_ja(dominant.get("name", ""))
            d_score = dominant.get("score", 0)
            top5 = _top_emotions(seg.get("emotions", {}), 5)
            top_str = ", ".join(f"{_emotion_ja(n)}({s:.2f})" for n, s in top5)
            parts.append(f"  Dominant: {d_name}({d_score:.2f})")
            parts.append(f"  Top 5: {top_str}")
            parts.append("")

    return "\n".join(parts)


def generate_spot_prompt(
    transcription: Optional[str],
    behavior_data: Optional[list],
    emotion_data: Optional[Union[list, Dict]] = None,
    recorded_at: str = "",
    timezone_str: str = "",
    subject_info: Optional[Dict] = None,
    local_time: Optional[str] = None,
    whisper_data: Optional[Dict] = None
) -> str:
    """
    Generate comprehensive LLM analysis prompt for spot recording

    Args:
        transcription: Transcribed text content (ASR, no timestamps)
        behavior_data: Behavior analysis results (SED, per-second events)
        emotion_data: Hume v3 dict (48 emotions) or legacy list (4 emotions) or None
        recorded_at: UTC timestamp in ISO 8601 format
        timezone_str: Device timezone (e.g., "Asia/Tokyo")
        subject_info: Subject information
        local_time: Local datetime string from database (e.g., "2025-11-16 12:31:01.485")

    Returns:
        Complete LLM analysis prompt
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
            # ERROR: local_time is required, do not use UTC
            print(f"ERROR: local_time not provided for {recorded_at}")
            hour = 0
            minute = 0
            local_date = "unknown"
            local_time_str = "??:??:??"

    except Exception as e:
        print(f"ERROR processing local_time: {e}")
        hour = 0
        minute = 0
        local_date = "unknown"
        local_time_str = "??:??:??"

    # Get time period
    time_period = get_time_period(hour)

    # Get weekday and holiday information
    weekday_info = get_weekday_info(local_date)
    holiday_info = get_holiday_context(local_date)

    # Get season
    month = int(local_date.split('-')[1])
    season = get_season(month)

    # Detect emotion format
    hume_mode = _is_hume_format(emotion_data)

    # Calculate duration from data
    has_behavior = behavior_data and len(behavior_data) > 0
    has_emotion = emotion_data is not None and (
        (isinstance(emotion_data, list) and len(emotion_data) > 0) or
        (isinstance(emotion_data, dict) and emotion_data.get("total_segments", 0) > 0)
    )
    if has_behavior:
        duration = len(behavior_data)
    elif has_emotion and not hume_mode:
        duration = len(emotion_data) * 10
    else:
        duration = 60

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
  "emotion": "最も有意な感情1-2個（カンマ区切り）",
  "rating": 0
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
- emotion: 1-2 most significant emotions in Japanese from SER data (例: 困惑, 楽しさ, 穏やかさ)
- If conversation/speech is detected in SED data, "会話" MUST be included in behavior field
- emotion field: Use Japanese emotion names from the Hume AI analysis (48 emotion categories available)
- JSON comments are for documentation only - do not include in output

**rating (0または1の整数):**
- **目的**: 発話の有無を判定
- **判定基準（必ず以下のルールに従うこと）**:
  - **0**: ASRセクションに発話内容がない場合
  - **1**: ASRセクションに何らかの会話・発話内容がある場合
- **重要**: SEDにSpeechやChild singingが検出されていても、ASRに発話がなければ必ず0にすること
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

    # ==================== 4. Unified Analysis Timeline ====================
    has_words = (whisper_data and isinstance(whisper_data, dict)
                 and whisper_data.get("words"))

    if has_words:
        # New format: unified 5s timeline with ASR + SED + SER
        prompt_parts.append(
            _build_unified_timeline(whisper_data, behavior_data, emotion_data, block_seconds=5)
        )
    else:
        # Legacy fallback: separate sections for old data without word timestamps
        prompt_parts.append("\n# vibe_transcriber_result\n")
        if transcription and transcription.strip():
            prompt_parts.append(f"{transcription}\n")
        else:
            prompt_parts.append("(No speech detected or transcription failed)\n")

        prompt_parts.append("\n# behavior_extractor_result Timeline\n")
        if not has_behavior:
            prompt_parts.append("(No behavior data available)\n")
        else:
            for entry in behavior_data:
                t = entry.get("time", 0)
                events = entry.get("events", [])
                if events:
                    sorted_events = sorted(events, key=lambda x: x.get("score", 0), reverse=True)[:3]
                    prompt_parts.append(f"## {t}s")
                    for ev in sorted_events:
                        label = ev.get("label", "Unknown")
                        score = ev.get("score", 0) * 100
                        prompt_parts.append(f"  - {label}: {score:.0f}%")
                    prompt_parts.append("")

        if has_emotion and hume_mode:
            skip_emotion = (
                not transcription or not transcription.strip()
                or transcription.strip() in ["(No speech detected or transcription failed)", ""]
            )
            prompt_parts.append(_format_hume_emotion_section(emotion_data, skip_emotion))
        elif not has_emotion:
            prompt_parts.append("\n# emotion_extractor_result\n\n(No emotion data available)\n")

    # ==================== 5. Analysis Guidelines ====================
    prompt_parts.append("""
# Analysis Process

**Step 1: Create Summary**
Based on the timeline above (ASR speech, SED acoustic events, SER emotions), describe what happened in 2-3 sentences.

**Priority for Summary:**
1. **ASR** - PRIMARY SOURCE: What was said? Who was speaking?
2. **SED** - CONTEXT: What activities/sounds were happening?
3. **SER** - REFERENCE: How did they seem to feel? (use cautiously)

**Step 2: Determine Vibe Score**

**判定フロー（この順番で必ず実行）**:

1. **まず発話の有無で分岐**:
   - ASRセクションに発話がない → ケースAへ
   - 発話内容がある → ケースBへ

**ケースA: 発話なし（-5 to +5の範囲内）**
SEDのみで判定:
- 静寂が多い → 0付近
- 音楽やTV音 → +2〜3
- 物音、生活音 → ±2
- **最終スコア: 必ず-5 to +5の範囲内**

**ケースB: 発話あり（-100 to +100の範囲）**
主にASRの内容で判定:

a) 内容分析（基本スコア）:
   - ポジティブ（楽しい、できた、すごい、褒める）→ +30 to +60
   - ニュートラル（日常会話、質問と回答）→ -20 to +20
   - ネガティブ（やめて、だめ、食べないで、泣き、叱責）→ -60 to -30

b) SEDで補正（±10まで）:
   - Laughter検出 → +10
   - Crying検出 → -10
   - その他の活動音 → ±5

**重要**: SER（感情分析）はvibe_score計算に使用しない

**Step 3: Extract Significant Emotions**
Based on the SER data in the timeline:
- Identify the 1-2 dominant emotions from the Hume AI analysis
- Use Japanese emotion names (e.g. 困惑, 楽しさ, 苦悩, 穏やかさ, 不安, 喜び, 怒り, 悲しみ)
- Consider speech_prosody as primary source, vocal_burst and language as supplementary
- If no speech detected, use "中立" as default
- Example output: "困惑, 楽しさ" or "穏やかさ"
""")

    return "\n".join(prompt_parts)
