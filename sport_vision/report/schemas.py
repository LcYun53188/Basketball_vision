from __future__ import annotations

import datetime
from typing import Optional, Any
from pydantic import BaseModel

class ReportBase(BaseModel):
    session_id: int
    report_text: str
    summary_json: Optional[dict[str, Any]] = None
    model_name: str = "gemini-3.5-flash"

class ReportGenerateRequest(BaseModel):
    session_id: int
    prompt_override: Optional[str] = None

class ReportResponse(ReportBase):
    id: int
    generated_at: datetime.datetime

    class Config:
        from_attributes = True
