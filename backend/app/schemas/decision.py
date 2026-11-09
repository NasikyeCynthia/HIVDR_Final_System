from typing import Literal
from pydantic import Field
from .common import StrictModel
class DecisionRequest(StrictModel):
    decision: Literal['Maintained', 'Substituted', 'Switched']
    decision_notes: str = Field(min_length=1, max_length=5000)
    recommended_regimen: str = Field(min_length=1, max_length=300)

class ImplementationRequest(StrictModel):
    implementation_notes: str = Field(min_length=1, max_length=5000)
