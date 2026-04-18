#import sklearn # 🚀 JETSON TLS FIX: Must be imported absolutely first
#import torch   # 🚀 JETSON TLS FIX: Must be imported second

import os
# 🚀 JETSON FIX: Prevents crashes from broken aarch64 torchcodec libraries
os.environ["TRANSFORMERS_NO_TORCHCODEC"] = "1"

import json
import re
import glob
import torch
import numpy as np
import soundfile as sf
import librosa
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from transformers import pipeline as hf_pipeline
from peft import PeftModel
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ============================================
# CONFIGURATIONS
# ============================================
BASE_MODEL_ID = "mesolitica/malaysian-whisper-medium-v2"
ADAPTER_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "rojak_medium_lora_adapter")
TARGET_SR = 16000
INSTANCE_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), "instance")
os.makedirs(INSTANCE_FOLDER, exist_ok=True)

# ============================================
# FILE MANAGEMENT HELPERS
# ============================================
def _to_safe_visit_id(patient_id):
    return str(patient_id).replace(" ", "_").replace("/", "_")


def clear_old_audio(patient_id):
    safe_vid = _to_safe_visit_id(patient_id)
    # The wildcard * ensures it catches chunks, full.wav, and temp.wav
    pattern = os.path.join(INSTANCE_FOLDER, f"visit_{safe_vid}_*") 
    for file_path in glob.glob(pattern):
        try:
            os.remove(file_path)
            print(f"🧹 Cleaned up Jetson storage: {file_path}")
        except OSError as e:
             print(f"⚠️ Could not delete {file_path}: {e}")
             
# def clear_old_audio(patient_id):
#     safe_vid = _to_safe_visit_id(patient_id)
#     pattern = os.path.join(INSTANCE_FOLDER, f"visit_{safe_vid}_*.wav")
#     for file_path in glob.glob(pattern):
#         try:
#             os.remove(file_path)
#             print(f"🧹 Cleaned up Jetson storage: {file_path}")
#         except OSError:
#             pass

# ============================================
# 🚀 L4 GPU OPTIMIZATION: GLOBAL CACHING
# ============================================
_asr_processor = None
_asr_model = None

# ============================================
# 1. ASR ENGINE (Whisper)
# ============================================
def get_asr():
    global _asr_processor, _asr_model
    if _asr_model is None:
        print("🚀 Loading Whisper to L4 GPU...")
        _asr_processor = WhisperProcessor.from_pretrained(BASE_MODEL_ID)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _asr_model = WhisperForConditionalGeneration.from_pretrained(
            BASE_MODEL_ID, 
            torch_dtype=torch.float16,
            device_map={"": device} 
        )
        if os.path.isdir(ADAPTER_DIR):
            _asr_model = PeftModel.from_pretrained(_asr_model, ADAPTER_DIR)
            _asr_model = _asr_model.merge_and_unload()
            _asr_model = _asr_model.to(device)
        _asr_model.eval()
    return _asr_processor, _asr_model

def transcribe_wav(audio_path):
    processor, model = get_asr()
    audio = _load_audio(audio_path)
    inputs = processor(audio, return_tensors="pt", sampling_rate=TARGET_SR)
    input_features = inputs.input_features.to("cuda", dtype=torch.float16)
    with torch.no_grad():
        generated_ids = model.generate(input_features, max_new_tokens=440)
    text = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return text.strip()

def transcribe_with_timestamps(audio_path):
    """Returns raw text chunks using HF Pipeline to prevent OOM."""
    processor, model = get_asr()
    asr_pipeline = hf_pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        torch_dtype=torch.float16,
        device=0 if torch.cuda.is_available() else -1,
        return_timestamps=True,
        chunk_length_s=30 
    )
    result = asr_pipeline(audio_path, batch_size=8, generate_kwargs={"max_new_tokens": 440})
    
    # VRAM CLEANUP
    del asr_pipeline
    torch.cuda.empty_cache()
    
    return result.get("chunks", [])

def _load_audio(path: str, target_sr: int = 16000) -> np.ndarray:
    audio, sr = sf.read(path, dtype="float32", always_2d=False)
    if audio.ndim > 1: 
        audio = np.mean(audio, axis=1).astype(np.float32)
    if sr != target_sr:
        audio = librosa.resample(audio, orig_sr=sr, target_sr=target_sr).astype(np.float32)
    return audio

# ============================================
# 2. SEMANTIC DIARIZATION ENGINE (The "Who" Logic)
# ============================================
def generate_diarized_transcript(patient_id):
    """Step 1: Gathers chunks, transcribes them, and performs Semantic Diarization."""
    safe_vid = _to_safe_visit_id(patient_id)
    
    # Finds ALL chunks mathematically, skipping none
    pattern = os.path.join(INSTANCE_FOLDER, f"visit_{safe_vid}_chunk*.wav")
    chunk_files = glob.glob(pattern)
    
    if not chunk_files:
        return "No audio found for this consultation."
        
    # Sort files by their exact number so the audio is in perfect chronological order
    chunk_files.sort(key=lambda x: int(re.search(r'chunk(\d+)\.wav', x).group(1)))
    
    print("🎙️ Step 1: Transcribing chunks individually to bypass timestamp hallucinations...")
    
    raw_text_pieces = []
    for chunk_path in chunk_files:
        try:
            # Transcribe each pre-sliced chunk
            text = transcribe_wav(chunk_path)
            if text:
                raw_text_pieces.append(text)
        except Exception as e:
            print(f"❌ Error transcribing {chunk_path}: {e}")
            
    # Glue the transcribed TEXT strings together and inject the Anchor
    raw_text = " ".join(raw_text_pieces).strip()
    raw_text = raw_text + "\n\n[END OF CONSULTATION]"
    
    print(f"\n--- RAW ASR TEXT ---\n{raw_text}\n--------------------\n")
    
    print("🧠 Step 2: Calling OpenAI API for Semantic Diarization...")
    try:
        response = client.chat.completions.create(
            model="gpt-4o", 
            messages=[
                {
                    "role": "system", 
                    "content": (
                        "You are a strict medical transcriptionist. Format this raw, messy ASR transcript into a clean 'Doctor:' and 'Patient:' dialogue. Whenever theres a change in speaker, make it into a new line"
                        "CRITICAL RULES:\n"
                        "1. DIARIZATION: Accurately assign speakers. Pay attention to context.\n"
                        "2. MEDICAL & PHONETIC CORRECTIONS: The ASR makes severe phonetic mistakes with Malaysian accents. You MUST correct them based on clinical context "
                        "(e.g., changing 'very cold winds' to 'varicose veins', 'weakness insufficient' to 'venous insufficiency', 'kulali' to 'buku lali', 'lift a dent' to 'leave a dent', 'other bawah ubat' to 'ada bawa ubat', 'bulit' to 'kulit').\n"
                        "3. MANDATORY HTML TAGS: Every single time you correct an ASR misheard word, you ABSOLUTELY MUST wrap the corrected word in exact HTML tags. "
                        "Do not skip this HTML formatting. Example: <span class='text-red-600 font-bold'>varicose veins</span>.\n"
                        "4. THE ANCHOR RULE: The raw text ends with the phrase [END OF CONSULTATION]. You MUST process every single word of the transcript and you are forbidden from stopping until you output the phrase [END OF CONSULTATION] exactly as it appears.\n\n"
                        "--- EXAMPLE ---\n"
                        "Raw Input: Doctor family history of very cold winds Patient my mother had very cold winds Doctor that can worsen the weakness issue Patient yes Doctor possible weakness insufficient features [END OF CONSULTATION]\n"
                        "Expected Output:\n"
                        "Doctor: Family history of <span class='text-red-600 font-bold'>varicose veins</span>?\n"
                        "Patient: My mother had <span class='text-red-600 font-bold'>varicose veins</span>.\n"
                        "Doctor: That can worsen the <span class='text-red-600 font-bold'>venous</span> issue.\n"
                        "Patient: Yes.\n"
                        "Doctor: Possible <span class='text-red-600 font-bold'>venous insufficiency</span> features.\n"
                        "[END OF CONSULTATION]\n"
                        "--- END OF EXAMPLE ---\n\n"
                        "Now, process the following transcript exactly like the example above."
                    )
                },
                {
                    "role": "user", 
                    "content": "Raw Input:\n" + raw_text
                }
            ],
            temperature=0.0,
            max_tokens=4000
        )
        final_transcript = response.choices[0].message.content.strip()
        final_transcript = final_transcript.replace("[END OF CONSULTATION]", "").strip()
        
    except Exception as e:
        print(f"❌ OpenAI API Error: {e}")
        return f"OpenAI formatting failed. Raw text:\n\n{raw_text}"
        
    return final_transcript

#Translation task
def translate_rojak(numbered_text):
    """Translate Rojak transcript to formal English."""
    print("🧠 Calling OpenAI API for Rojak Translation...")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a medical translator specializing in "
                        "Malaysian multilingual clinical conversations.\n\n"
                        "Translate the following transcript into formal English.\n"
                        "The transcript may contain:\n"
                        "- Bahasa Melayu\n"
                        "- English\n"
                        "- Mandarin (romanized or characters)\n"
                        "- Bahasa Kelantan dialect\n"
                        "- Mixed code-switching between any of the above\n\n"
                        "Rules:\n"
                        "1. Translate ALL non-English content to English.\n"
                        "2. Preserve medical terms exactly as stated.\n"
                        "3. Preserve ALL line number tags [L1], [L2] etc. exactly "
                        "as they appear. Do NOT remove or renumber them.\n"
                        "4. Do NOT add information not present in the original.\n"
                        "5. If a word or phrase is unclear or you are unsure of "
                        "the translation, write [UNCLEAR: original text].\n"
                        "6. Maintain speaker labels (Doctor/Patient).\n"
                        "7. Do NOT interpret or add clinical meaning — "
                        "translate literally."
                    ),
                },
                {"role": "user", "content": numbered_text},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"❌ Translation failed: {e}")
        return None


def process_clinical_tasks(labeled_text):
    """Step 2: Extracts the 5 specific boxes you created."""
    print("⏳ GPT is structuring medical notes...")
    
    # We force the output to be a JSON object with your specific boxes
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system", 
                "content": (
                    "Extract medical details from the transcript into English. "
                    "You must return a JSON object with these exact keys: "
                    "'chief_complaint', 'hpi', 'pmh', 'meds', 'social', 'allergies'. "
                    "Values must be plain strings summarizing the findings."
                    "You must add bullet points in front of each new sentence."
                    "Each new sentence must be in a new line."
                )
            },
            {"role": "user", "content": labeled_text}
        ]
    )
    
    # This safely turns the string response into a Python dictionary
    return json.loads(response.choices[0].message.content)

def run_post_consultation_pipeline(patient_id):
    """Updated to accept patient_id so it can locate the chunk files."""
    # Step A & B: Get raw text from chunks and Diarize
    labeled = generate_diarized_transcript(patient_id)
    
    # Step C: Extract medical notes (Leaving untouched as requested!)
    structured = process_clinical_tasks(labeled)

    return {
        "labeled_transcript": labeled,
        "medical_notes": structured 
    }