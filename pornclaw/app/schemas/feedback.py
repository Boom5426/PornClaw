from typing import Literal

from pydantic import BaseModel


FeedbackType = Literal["like", "dislike", "skip", "more_like_this", "less_like_this"]


class FeedbackRequest(BaseModel):
    session_id: int
    series_id: int
    feedback_type: FeedbackType


class FeedbackResponse(BaseModel):
    ok: bool
    updated_profile_summary: dict
