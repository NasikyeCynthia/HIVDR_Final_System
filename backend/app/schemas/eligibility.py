from datetime import date
from typing import Literal
from pydantic import Field
from .common import StrictModel


class IACSessionCreate(StrictModel):
    session_date: date
    adherence_pct: float = Field(ge=0, le=150)
    method: Literal['Pill count', 'Self-report', 'Pharmacy refill'] = 'Pill count'
    barriers: str = Field(default='', max_length=5000)


class ReferralRequest(StrictModel):
    basis: Literal['guideline', 'clinician_override'] = 'guideline'
    reason: str = Field(default='', max_length=5000)
