from typing import Literal, Optional
from pydantic import Field
from .common import StrictModel


class CollectionRecord(StrictModel):
    correction_reason: str = Field(default='', max_length=3000)
    sample_type: Literal['Plasma', 'DBS']
    collected_at: str = Field(min_length=10, max_length=32)
    centrifuged_at: Optional[str] = Field(default=None, max_length=32)
    tubes: Optional[int] = Field(default=None, ge=0, le=6)
    whole_blood_ml: Optional[float] = Field(default=None, ge=0, le=30)
    storage_temp: Optional[str] = Field(default=None, max_length=40)
    dbs_reason: str = Field(default='', max_length=200)
    dbs_note: str = Field(default='', max_length=3000)
    officer_name: str = Field(default='', max_length=200)
    officer_phone: str = Field(default='', max_length=30)


class DispatchRecord(StrictModel):
    correction_reason: str = Field(default='', max_length=3000)
    dispatched_at: str = Field(min_length=10, max_length=32)


class ReceiptChecks(StrictModel):
    id_matches: bool = True          # ART number on the sample matches the form
    form_has_id: bool = True         # request form has the patient's ART or other number
    not_haemolysed: bool = True
    tube_not_empty: bool = True
    volume_ok: bool = True           # at least 1 mL plasma


class ReceiptRecord(StrictModel):
    correction_reason: str = Field(default='', max_length=3000)
    received_at: str = Field(min_length=10, max_length=32)
    checks: ReceiptChecks = ReceiptChecks()
    repeat_vl: float | None = Field(default=None, ge=0)   # viral load from the same blood draw, run at CPHL
    repeat_vl_date: str | None = Field(default=None, max_length=10)
    outcome: Literal['Referred to DR lab', 'Deferred to facility', 'Rejected']
    plasma_volume_ml: Optional[float] = Field(default=None, ge=0, le=20)
    reason: str = Field(default='', max_length=200)
    note: str = Field(default='', max_length=3000)


class ResultRecord(StrictModel):
    outcome: Literal['Usable result', 'Unamplified', 'Sequencing failed']
    tested_at: str = Field(min_length=10, max_length=32)
    released_at: str = Field(min_length=10, max_length=32)
    failure_reason: str = Field(default='', max_length=3000)
    mutations: str = Field(default='', max_length=15000)
    sequence: str = Field(default='', max_length=100000)
    subtype: str = Field(default='', max_length=40)
    correction_reason: str = Field(default='', max_length=3000)
    nrti: str = Field(default='', max_length=3000)
    nnrti: str = Field(default='', max_length=3000)
    pi_major: str = Field(default='', max_length=3000)
    pi: str = Field(default='', max_length=3000)
    pi_minor: str = Field(default='', max_length=3000)
    insti: str = Field(default='', max_length=3000)
    other: str = Field(default='', max_length=3000)
    drug_levels: dict[str, str] = Field(default_factory=dict)


class RepeatRequest(StrictModel):
    note: str = Field(default='', max_length=3000)


class MutationRecord(StrictModel):
    pi: str = Field(default='',max_length=5000)
    insti: str = Field(default='',max_length=5000)
    nrti: str = Field(default='',max_length=5000)
    nnrti: str = Field(default='',max_length=5000)
    expected_version: int = Field(ge=0)
    expected_lab_version: int = Field(ge=0)
    reason: str = Field(min_length=10,max_length=3000)
