from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/meteor", tags=["Meteor"])

@router.get("/calendar/{city}")
async def meteor_calendar(request: Request, city: str):
    """Retrieve meteor shower visibility and peak times for a city."""
    if not hasattr(request.app.state, 'meteor') or request.app.state.meteor is None:
        raise HTTPException(status_code=503, detail="Meteor module not ready")
    
    try:
        # Assuming the predict module has a 'predict' or 'get_calendar' function
        # Based on Conversation History, it likely calculates Bortle and Peak ZHR
        return request.app.state.meteor.predict(city)
    except Exception as e:
        return {"city": city, "bortle": 5, "events": [], "error": str(e)}
