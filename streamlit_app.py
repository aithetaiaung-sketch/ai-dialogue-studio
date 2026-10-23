import asyncio
import glob
import json
import os
import shutil
from datetime import datetime
import edge_tts
import google.generativeai as genai
import streamlit as st

CONFIG_FILE = "config.json"

VOICES = {
    "UK Female (Sonia)": "en-GB-SoniaNeural",
    "UK Male (Ryan)": "en-GB-RyanNeural",
    "US Female (Jenny)": "en-US-JennyNeural",
    "US Male (Guy)": "en-US-GuyNeural",
    "AU Female (Natasha)": "en-AU-NatashaNeural",
}

# Streamlit Page Setup
st.set_page_config(
    page_title="AI Dialogue Studio", page_icon="🎙️", layout="centered"
)

st.title("🎙️ AI Dialogue & Subtitle Studio")
st.caption("Generate English-Myanmar dialogues for TikTok with Edge-TTS")


# Load/Save Config
def load_config():
  if os.path.exists(CONFIG_FILE):
    try:
      with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      pass
  return {}


def save_config(api_key):
  try:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
      json.dump({"api_key": api_key}, f, ensure_ascii=False, indent=2)
  except Exception:
    pass


config_data = load_config()

# ----------------- Section 1: AI Script Generator -----------------
st.subheader("✨ Auto Script Generator (Gemini AI)")

col_api, col_topic = st.columns([1, 1])
with col_api:
  api_key = st.text_input(
      "Gemini API Key",
      value=config_data.get("api_key", ""),
      type="password",
      placeholder="Paste Gemini API Key...",
  )
with col_topic:
  topic = st.text_input("Topic", placeholder="e.g. Ordering Coffee")

if st.button("Generate Script", type="primary"):
  if not api_key:
    st.error("Please enter a valid Gemini API Key!")
  elif not topic:
    st.error("Please enter a Topic!")
  else:
    save_config(api_key)
    with st.spinner("AI is generating 10-line script..."):
      try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-3.8-flash")

        prompt = f"""
Create a natural 10-line English conversation (exactly 10 spoken lines, 5 turns each) between Speaker A and Speaker B about '{topic}'.

STRICT FORMAT RULES:
1. Format each English line as 'A: [English sentence]' or 'B: [English sentence]'.
2. Alternate between A and B precisely: A, B, A, B, A, B, A, B, A, B (Total 10 lines).
3. Right below each English sentence, write its natural Myanmar translation enclosed in parenthetical brackets '(မြန်မာဘာသာပြန်)'.
4. Do not include line numbers, intro, outro, title, or Markdown formatting (like ** or ```).
5. Keep English sentences natural, simple, and high-frequency for TikTok learners.
"""

        response = model.generate_content(prompt)
        st.session_state["script_text"] = response.text.strip()
        st.success("10-Line Script Generated!")
      except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "Quota exceeded" in err_msg:
          st.error(
              "⚠️ API Rate Limit ပြည့်သွားပါသည်။ စက္ကန့် ၄၀ ခန့်"
              " စောင့်ပြီးမှ ပြန်စမ်းပါ။"
          )
        else:
          st.error(f"AI Error: {err_msg}")

# Default Text
default_script = st.session_state.get(
    "script_text",
    "A: Good morning! How are you doing today?\n(မင်္ဂလာနံနက်ခင်းပါ! ဒီနေ့"
    " နေကောင်းရဲ့လား။)\nB: I'm doing great, thank you! How about"
    " you?\n(ကျေးဇူးပါ၊ ကျွန်တော် နေကောင်းပါတယ်။ သင်ရော ဘယ်လိုလဲ။)",
)

# ----------------- Section 2: Script Editor -----------------
st.subheader("📝 Script Editor (English + Myanmar)")
script_input = st.text_area("Edit Script Here", value=default_script, height=220)

# ----------------- Section 3: Voice Settings -----------------
st.subheader("⚙️ Voice Settings")

col_spk1, col_spk2, col_spd = st.columns([2, 2, 1])
with col_spk1:
  speaker_a = st.selectbox("Speaker A", list(VOICES.keys()), index=0)
with col_spk2:
  speaker_b = st.selectbox("Speaker B", list(VOICES.keys()), index=1)
with col_spd:
  speed = st.selectbox("Speed", ["-10%", "+0%", "+10%", "+20%"], index=1)

# Voice Testing Buttons
col_test_a, col_test_b = st.columns(2)
with col_test_a:
  if st.button("▶ Test Speaker A Voice"):
    test_voice_a = VOICES[speaker_a]

    async def run_test_a():
      comm = edge_tts.Communicate(
          f"Hello! This is Speaker A using {speaker_a}.",
          test_voice_a,
          rate=speed,
      )
      await comm.save("test_a.mp3")

    asyncio.run(run_test_a())
    st.audio("test_a.mp3")

with col_test_b:
  if st.button("▶ Test Speaker B Voice"):
    test_voice_b = VOICES[speaker_b]

    async def run_test_b():
      comm = edge_tts.Communicate(
          f"Hello! This is Speaker B using {speaker_b}.",
          test_voice_b,
          rate=speed,
      )
      await comm.save("test_b.mp3")

    asyncio.run(run_test_b())
    st.audio("test_b.mp3")

# ----------------- Section 4: Process & Download -----------------
st.divider()

if st.button("⚡ Generate MP3 & SRT Subtitles", type="primary", use_container_width=True):
  raw_lines = [
      line.strip() for line in script_input.split("\n") if line.strip()
  ]

  dialogue_items = []
  for line in raw_lines:
    if (line.startswith("(") and line.endswith(")")) or (
        line.startswith("（") and line.endswith("）")
    ):
      clean_my = line[1:-1].strip()
      if dialogue_items:
        dialogue_items[-1]["my"] = clean_my
    else:
      spk = "A"
      clean_text = line
      if line.startswith("A:") or line.startswith("a:"):
        spk = "A"
        clean_text = line[2:].strip()
      elif line.startswith("B:") or line.startswith("b:"):
        spk = "B"
        clean_text = line[2:].strip()

      dialogue_items.append({"speaker": spk, "eng": clean_text, "my": ""})

  if not dialogue_items:
    st.error("Script Editor ထဲတွင် စာသားများ မရှိပါ!")
  else:
    progress_bar = st.progress(0)
    status_text = st.empty()

    status_text.text("Status: 1/2 Generating Audio...")

    voice_a = VOICES[speaker_a]
    voice_b = VOICES[speaker_b]

    temp_folder = "temp_audio"
    if os.path.exists(temp_folder):
      try:
        shutil.rmtree(temp_folder)
      except Exception:
        pass
    os.makedirs(temp_folder, exist_ok=True)

    durations = []

    async def run_tts():
      total = len(dialogue_items)
      for idx, item in enumerate(dialogue_items, start=1):
        sel_voice = voice_a if item["speaker"] == "A" else voice_b
        mp3_file = os.path.join(
            temp_folder, f"line_{idx:03d}_{item['speaker']}.mp3"
        )

        communicate = edge_tts.Communicate(item["eng"], sel_voice, rate=speed)
        last_end_sec = 0.0

        with open(mp3_file, "wb") as file:
          async for chunk in communicate.stream():
            if chunk["type"] == "audio":
              file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
              offset = chunk["offset"]
              duration = chunk["duration"]
              end_sec = (offset + duration) / 10000000.0
              if end_sec > last_end_sec:
                last_end_sec = end_sec

        if last_end_sec > 0:
          durations.append(last_end_sec)
        else:
          durations.append(max(1.0, os.path.getsize(mp3_file) / 6000.0))

        progress_bar.progress(int((idx / total) * 70))

    asyncio.run(run_tts())

    # Merge MP3
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    combined_mp3 = f"dialogue_{timestamp}.mp3"
    srt_file = f"dialogue_{timestamp}.srt"

    audio_files = sorted(glob.glob(os.path.join(temp_folder, "line_*.mp3")))
    with open(combined_mp3, "wb") as outfile:
      for file in audio_files:
        with open(file, "rb") as infile:
          outfile.write(infile.read())

    status_text.text("Status: 2/2 Generating Subtitles...")
    progress_bar.progress(85)

    def format_timestamp(seconds):
      hours = int(seconds // 3600)
      minutes = int((seconds % 3600) // 60)
      secs = int(seconds % 60)
      millisecs = int(round((seconds % 1) * 1000))
      if millisecs >= 1000:
        secs += 1
        millisecs -= 1000
      return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

    current_time = 0.0
    pause_duration = 0.3

    with open(srt_file, "w", encoding="utf-8") as f:
      for idx, item in enumerate(dialogue_items, start=1):
        start_time = current_time
        dur = durations[idx - 1]
        end_time = start_time + dur
        current_time = end_time + pause_duration

        start_str = format_timestamp(start_time)
        end_str = format_timestamp(end_time)

        eng_text = item["eng"]
        my_text = item["my"]

        if my_text:
          f.write(
              f"{idx}\n{start_str} --> {end_str}\n{eng_text}\n({my_text})\n\n"
          )
        else:
          f.write(f"{idx}\n{start_str} --> {end_str}\n{eng_text}\n\n")

    progress_bar.progress(100)
    status_text.success("Complete! Download your files below:")

    # Audio Player & Download Buttons
    st.audio(combined_mp3)

    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
      with open(combined_mp3, "rb") as f_mp3:
        st.download_button(
            "📥 Download Audio (MP3)",
            f_mp3,
            file_name=combined_mp3,
            mime="audio/mp3",
            use_container_width=True,
        )
    with col_dl2:
      with open(srt_file, "rb") as f_srt:
        st.download_button(
            "📥 Download Subtitle (SRT)",
            f_srt,
            file_name=srt_file,
            mime="text/plain",
            use_container_width=True,
        )