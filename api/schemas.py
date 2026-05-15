from typing import Dict, Union

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
