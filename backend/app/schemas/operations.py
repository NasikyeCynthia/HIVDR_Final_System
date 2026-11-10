from typing import Literal
from pydantic import Field
from .common import StrictModel
class RecordFieldsUpdate(StrictModel):
    expected_version:int=Field(ge=0)
    fields:dict[str,str]
class ArchiveRequest(StrictModel):
    archived:bool
    reason:str=Field(min_length=3,max_length=2000)
class AccountCreate(StrictModel):
    username:str=Field(min_length=3,max_length=80,pattern=r'^[a-zA-Z0-9_.-]+$')
    name:str=Field(min_length=1,max_length=200)
    role:Literal['nurse','counsellor','lab','clinician']
    facility:str=Field(min_length=1,max_length=200)

class AmendmentRequest(StrictModel):
    reason:str=Field(min_length=10,max_length=3000)
