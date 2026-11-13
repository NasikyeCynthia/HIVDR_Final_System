from typing import Literal
from pydantic import Field
from .common import StrictModel
class DecisionRequest(StrictModel):
    decision: Literal['Maintained', 'Substituted', 'Switched']
    decision_notes: str = Field(min_length=1, max_length=5000)
    recommended_regimen: str = Field(min_length=1, max_length=300)
    expected_version: int | None = Field(default=None,ge=0)
    expected_data_version: int | None = Field(default=None,ge=0)
    evidence_reviewed: bool = False

class ImplementationRequest(StrictModel):
    implementation_notes: str = Field(min_length=1, max_length=5000)
    start_date: str | None = Field(default=None, max_length=10)
    started_regimen: str = Field(default='', max_length=300)
    previous_stop_date: str | None = Field(default=None, max_length=10)

class FollowUpRequest(StrictModel):
    care_status: str = Field(min_length=1, max_length=80)
    vl_copies: float | None = Field(default=None, ge=0)
    vl_date: str | None = Field(default=None, max_length=10)
    regimen: str = Field(default='', max_length=300)
    psychosocial: str = Field(default='', max_length=3000)
    clinical_status: str = Field(default='', max_length=3000)
    notes: str = Field(default='', max_length=5000)
