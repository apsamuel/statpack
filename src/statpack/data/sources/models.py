from pydantic import BaseModel, Field
import time


class Request(BaseModel):
    url: str
    params: dict | None = None
    request_headers: dict | None = None
    response_headers: dict | None = None


class FailedRequest(BaseModel):
    url: str
    status_code: int
    reason: str
    timestamp: float = Field(default_factory=time.time)
