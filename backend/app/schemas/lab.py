from typing import Literal
from pydantic import Field
from .common import StrictModel
class LabUpdate(StrictModel):
    sample_type: Literal['Plasma', 'DBS']
    status: Literal['Pending', 'Usable result', 'Unamplified', 'Sequencing failed']
    dbs_reason: str = Field(default='', max_length=3000)
    failure_reason: str = Field(default='', max_length=3000)
    mutations: str = Field(default='', max_length=15000)
