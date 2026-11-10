from typing import Literal
from pydantic import Field
from .common import StrictModel
class PsychosocialUpdate(StrictModel):
    assessed: bool = False
    factors: list[str] = Field(default_factory=list, max_length=30)
    notes: str = Field(default='', max_length=5000)
class InterpretationRequest(StrictModel):
    kind: Literal['mutations','sequence']
    text: str = Field(min_length=1,max_length=100000)
class UserUpdate(StrictModel):
    name: str = Field(min_length=1,max_length=200)
    facility: str = Field(min_length=1,max_length=200)
    can_access_all: bool = False

class LabAssignmentRequest(StrictModel):
    lab_owner: int = Field(gt=0)

class ReviewRequest(StrictModel):
    notes: str = Field(min_length=1,max_length=5000)
