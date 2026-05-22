from typing import Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


Num = Union[int, float]
Cat = Union[int, str]


class PredictRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    age: int = Field(alias="AGE")
    sex: Cat = Field(alias="SEX")
    bmi: float = Field(alias="BMI")
    sp: Num = Field(alias="SP")
    bp: Num = Field(alias="BP")
    hba1c: float = Field(alias="HbA1c")
    fps: Num = Field(alias="FPS")
    pps: Num = Field(alias="PPS")
    fam_ho: Cat = Field(alias="FAMILY H/O")
    on_age: Num = Field(alias="ONSET AGE")
    dia_life: Union[Num, str] = Field(alias="DIA LIFE")
    smk: Cat = Field(alias="SMOKING")
    phy_act: Cat = Field(alias="PHY ACT")
    med_use: Cat = Field(alias="MED USE")
    med_adh: Cat = Field(alias="MED ADH")


class PredictResponse(BaseModel):
    risk_scores: Dict[str, float]
    risk_labels: Dict[str, int]
    risk_level: str
    warning_message: str
    model_name: str
    model_version: str


class TruthLabels(BaseModel):
    nep: Optional[int] = Field(default=None, alias="NEP")
    neu: Optional[int] = Field(default=None, alias="NEU")
    ret: Optional[int] = Field(default=None, alias="RET")
    cv: Optional[int] = Field(default=None, alias="CV")
    per_vas: Optional[int] = Field(default=None, alias="PER VAS")


class IngestRequest(PredictRequest):
    patient_id: int
    patient_name: str
    source: str = "his"
    source_idx: Optional[int] = None
    truth: Optional[TruthLabels] = None


class IngestResponse(PredictResponse):
    saved: bool
    already_saved: bool
    patient_id: int
    clinical_record_id: int
    prediction_id: int
    alert_ids: List[int]
    watchlist_ids: List[int]
    truth_saved: bool
    request_log_id: Optional[int] = None
