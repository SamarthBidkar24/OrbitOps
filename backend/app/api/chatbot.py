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

# Rate limiting - module level dict
rate_store = defaultdict(list)

@router.post("/chat")
async def chat_endpoint(request: Request, body: ChatRequest):
    """
    Handle incoming chatbot questions with streaming Gemini response.
    Supports multi-turn conversation and multi-language responses.
    """
    
    # Rate limiting check
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

    # Build messages list
    gemini_history = []
    for msg in body.conversation_history:
        role = "model" if msg["role"] == "assistant" else "user"
        gemini_history.append({"role": role, "parts": [msg["content"]]})

    # System prompt
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

    # List of candidate models to try (updated for 2026)
    model_candidates = [
        'gemini-3.1-flash-live-preview',
        'gemini-3.1-flash',
        'gemini-2.5-flash',
        'gemini-1.5-flash-latest',
        'deep-research-pro-preview-12-2'
    ]

    def generate():
        selected_model = None
        for candidate in model_candidates:
            try:
                test_model = genai.GenerativeModel(model_name=candidate)
                chat_session = test_model.start_chat(history=gemini_history)
                selected_model = candidate
                print(f"✓ Chatbot using model: {selected_model}")
                break
            except Exception:
                continue

        if not selected_model:
            print("✘ Chatbot Error: All models failed. Falling back to Mock mode.")
            msg_lower = body.message.lower()
            if "darkest sky" in msg_lower or "hanle" in msg_lower or "ladakh" in msg_lower:
                mock_text = ("The darkest sky in India is found at Hanle in Ladakh.")
            elif "hello" in msg_lower or "hi" in msg_lower:
                mock_text = "Greetings! I am AkashBot. How can I assist you with OrbitOps today?"
            else:
                mock_text = "I'm in mock mode as I couldn't reach the Gemini API."
            
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
            yield f"data: {json.dumps('Streaming error')}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )
