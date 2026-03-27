from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class AuthRequest(BaseModel):
    initData: str

class GiveawayPublishSchema(BaseModel):
    title: str
    template_id: int
    button_text: str
    button_emoji: str
    sponsor_channels: List[int]
    publish_channels: List[int]
    result_channels: List[int]
    start_immediately: bool
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    winners_count: int
    use_boosts: bool
    use_invites: bool
    max_invites: int
    use_stories: bool
    use_captcha: bool

class JoinGiveawayRequest(BaseModel):
    ref_code: str | None = None