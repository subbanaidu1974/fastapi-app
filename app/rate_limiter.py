from fastapi import HTTPException
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
from redis_client import r

RATE_LIMIT = 10  # max requests
RATE_LIMIT_PERIOD = 60  # seconds

def rate_limit(api_key: str):
    try:
        key = f"rate_limit:{api_key}"
        current = r.get(key)
        if current and int(current) >= RATE_LIMIT:
            raise HTTPException(status_code=429, detail="Rate limit exceeded.")

        pipe = r.pipeline()
        pipe.incr(key, 1)
        pipe.expire(key, RATE_LIMIT_PERIOD)
        pipe.execute()
    except Exception as e:
        print(f"Rate limiter error: {e}")
        # Optional: either block or allow on error, your call
        # For now, allow if Redis is down

