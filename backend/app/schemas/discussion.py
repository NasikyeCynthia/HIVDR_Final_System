from pydantic import Field
from .common import StrictModel
class DiscussionRequest(StrictModel):
    body: str = Field(min_length=1, max_length=5000)
