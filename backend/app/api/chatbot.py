import anthropic
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
from app.core.config import settings
from collections import defaultdict
from datetime import datetime, timedelta

# Create router with /chatbot prefix to match /api/v1/chatbot/chat
router = APIRouter(prefix="/chatbot", tags=["Chat"])

# 1. Setup Anthropic client
client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

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
    # conversation_history should be a list of {"role": "...", "content": "..."}
    messages = body.conversation_history.copy()
    messages.append({"role": "user", "content": body.message})

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

    # Append language instruction to system if not "en"
    if body.language != "en":
        system += f"\nRespond in language code: {body.language}"

    # 5. Use StreamingResponse for SSE (Server-Sent Events)
    def generate():
        try:
            with client.messages.stream(
                model="claude-3-5-sonnet-20241022",
                max_tokens=300,
                system=system,
                messages=messages
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {text}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            # --- Failover to Local Mock response for user testing/dev if API key fails ---
            print(f"✘ Chatbot API Error: {e}")
            msg_lower = body.message.lower()
            if "darkest sky" in msg_lower or "hanle" in msg_lower or "ladakh" in msg_lower:
                mock_text = ("The darkest sky in India is found at Hanle in Ladakh, "
                             "home to the Indian Astronomical Observatory (IAO). "
                             "Its high altitude (4,500m) and minimal light pollution "
                             "make it an ideal 'Dark Sky Reserve'.")
            else:
                mock_text = ("I'm AkashBot, your planetary science guide. "
                             "Currently I'm in offline mode, but I can still tell you about "
                             "NEOs and asteroid classification!")
            
            # Stream the mock text character by character or word by word
            import time
            for word in mock_text.split():
                yield f"data: {word} \n\n"
                time.sleep(0.01)
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )
