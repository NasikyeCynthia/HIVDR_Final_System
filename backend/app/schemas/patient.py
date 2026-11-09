from typing import Literal
from pydantic import Field
from .common import StrictModel

class PatientCreate(StrictModel):
    external_id: str = Field(min_length=1, max_length=100)
    name: str = Field(default='', max_length=200)

class ProfileUpdate(StrictModel):
    name: str | None = Field(default=None, max_length=200)
    age: float | None = Field(default=None, ge=0, le=120)
    sex: str | None = Field(default=None, max_length=30)
    regimen: str | None = Field(default=None, max_length=300)
    treatment_line: Literal[1, 2, 3] | None = None
    viral_load: float | None = Field(default=None, ge=0)
    adherence: float | None = Field(default=None, ge=0, le=100)
    notes: str | None = Field(default=None, max_length=5000)

class AssignmentRequest(StrictModel):
    assigned_to: int = Field(gt=0)

class ImportRequest(StrictModel):
    source: Literal['original', 'synthetic']
    csv: str = Field(min_length=1, max_length=40000000)
