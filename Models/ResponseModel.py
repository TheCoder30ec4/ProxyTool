from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class UserResponseModel(BaseModel):
    """Response model for user information."""

    id: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class ResumeDetailResponseModel(BaseModel):
    """Response model for resume detail information."""

    id: str
    message: str
    resume_details: Optional[str]
    created_at: Optional[str]  # ISO format string
    role: str

    model_config = ConfigDict(from_attributes=True)


class ResumeDetailsListResponseModel(BaseModel):
    """Response model for list of resume details."""

    user_id: str
    user_email: str
    resume_count: int
    resume_details: List[ResumeDetailResponseModel]
