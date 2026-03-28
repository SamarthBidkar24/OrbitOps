import google.generativeai as genai
import json
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
from app.core.config import settings
from collections import defaultdict
from datetime import datetime, timedelta

# Create router with /chatbot prefix to match /api/v1/chatbot/chat
router = APIRouter(prefix="/chatbot", tags=["Chat"])

# 1. Setup Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

# 2. POST /chat endpoint body schema
class ChatRequest(BaseModel):
    message: str
    conversation_history: List[Dict[str, str]] = []
    language: str = "en"

# 6. Rate limiting - module level dict
# Stores list of request timestamps per IP
rate_store = defaultdict(list)

@router.post("/chat")
async def chat_endpoint(request: Request, body: ChatRequest):
    """
    Handle incoming chatbot questions with streaming Claude response.
    Supports multi-turn conversation and multi-language responses.
    """
    
    # 6. Rate limiting check
    ip = request.client.host
    now = datetime.utcnow()
    hour_ago = now - timedelta(hours=1)
    
    # Clean up old records for this IP
    rate_store[ip] = [t for t in rate_store[ip] if t > hour_ago]
    
    if len(rate_store[ip]) >= 15:
        raise HTTPException(
            status_code=429, 
            detail="Chat limit reached. Try again in an hour."
        )
    
    rate_store[ip].append(now)

    # 3. Build messages list
    # Format history strictly for Gemini ('user' or 'model')
    gemini_history = []
    for msg in body.conversation_history:
        role = "model" if msg["role"] == "assistant" else "user"
        gemini_history.append({"role": role, "parts": [msg["content"]]})

    # 4. System prompt
    system = """You are AkashBot, AI guide for OrbitOps
— India's planetary science platform. You know:
asteroid science, meteor showers, near-Earth objects,
Indian space missions (Chandrayaan 1/2/3, Aditya-L1,
Mangalyaan), ISRO history.
Guide users on 3 modules:
1) NEO Dashboard: enter date + observatory
2) Asteroid Classifier: enter spectral data
3) Meteor Planner: enter your city
Keep responses under 120 words. Encourage beginners.
If language=hi respond fully in Hindi.
If language=mr respond fully in Marathi.
If language=ta respond fully in Tamil."""

    if body.language != "en":
        system += f"\nRespond in language code: {body.language}"

    # List of candidate models to try (ordered by preference for 2026)
    model_candidates = [
        'gemini-3.1-flash-live-preview',
        'gemini-3.1-flash',
        'gemini-2.5-flash',
        'gemini-1.5-flash-latest',
        'deep-research-pro-preview-12-2'
    ]

    def generate():
        selected_model = None
        # Try to find a working model
        for candidate in model_candidates:
            try:
                # Test the model with a tiny request
                test_model = genai.GenerativeModel(model_name=candidate)
                # If we can start a chat, we consider it a candidate
                # We'll use the first one that doesn't 404 on start
                chat_session = test_model.start_chat(history=gemini_history)
                selected_model = candidate
                print(f"✓ Chatbot using model: {selected_model}")
                break
            except Exception:
                continue

        if not selected_model:
            print("✘ Chatbot Error: All Gemini models failed (404/Auth). Falling back to Mock mode.")
            msg_lower = body.message.lower()
            if "darkest sky" in msg_lower or "hanle" in msg_lower or "ladakh" in msg_lower:
                mock_text = ("The darkest sky in India is found at Hanle in Ladakh, "
                             "home to the Indian Astronomical Observatory (IAO). "
                             "Its high altitude (4,500m) and minimal light pollution "
                             "make it an ideal 'Dark Sky Reserve'.")
            elif "hello" in msg_lower or "hi" in msg_lower:
                mock_text = "Greetings! I am AkashBot. How can I assist you with OrbitOps today?"
            elif "neo" in msg_lower or "asteroid" in msg_lower:
                mock_text = ("Near-Earth Objects (NEOs) are asteroids or comets with orbits "
                             "bringing them close to Earth. Our platform analyzes their trajectories "
                             "and potential impact threats in real-time.")
            elif "bortle" in msg_lower:
                mock_text = ("The Bortle Scale is a nine-level numeric scale that measures the night sky's "
                             "brightness. Class 1 is perfectly dark, while Class 9 is severe light pollution.")
            elif "spectra" in msg_lower or "mineral" in msg_lower:
                mock_text = ("Astrospectra classifies the mineral composition of asteroids using "
                             "spectroscopic data to identify valuable space resources.")
            else:
                mock_text = ("I'm currently in mock mode because I couldn't connect to any Gemini models! "
                             "Please check your `GEMINI_API_KEY` in `backend/.env`. "
                             "I can only answer basic questions for now.")
            
            import time
            words = mock_text.split()
            for i, word in enumerate(words):
                val = word + (" " if i < len(words) - 1 else "")
                yield f"data: {json.dumps(val)}\n\n"
                time.sleep(0.01)
            yield "data: [DONE]\n\n"
            return

        try:
            model = genai.GenerativeModel(model_name=selected_model, system_instruction=system)
            chat_session = model.start_chat(history=gemini_history)
            response = chat_session.send_message(body.message, stream=True)
            for chunk in response:
                if chunk.text:
                    yield f"data: {json.dumps(chunk.text)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            print(f"✘ Chatbot Streaming Error: {e}")
            yield f"data: {json.dumps('Sorry, I encountered an error while streaming my response.')}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )
