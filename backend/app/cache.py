from typing import Optional

# In-memory dictionary to store processed NEO predictions
prediction_cache = {}

def get_cached(date: str, observatory: int) -> Optional[dict]:
    """Retrieve cached neo prediction result based on input keys."""
    key = f"neo:{date}:{observatory}"
    # Check if the exact search query exists in the cache
    if key in prediction_cache:
        print(f"✓ Cache hit for {key}")
        return prediction_cache[key]
    return None

def set_cached(date: str, observatory: int, result: dict):
    """Store neo prediction result in the memory cache for faster subsequent requests."""
    key = f"neo:{date}:{observatory}"
    prediction_cache[key] = result
    print(f"✓ Cached result for {key}")
