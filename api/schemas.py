from typing import Dict, Union

from pydantic import BaseModel


Num = Union[int, float]
Cat = Union[int, str]


class PredictRequest(BaseModel):
    age: int
    sex: Cat
    bmi: float
    sp: Num
    bp: Num
    hba1c: float
    fps: Num
    pps: Num
    fam_ho: Cat
    on_age: Num
    dia_life: Union[Num, str]
    smk: Cat
    phy_act: Cat
    med_use: Cat
    med_adh: Cat


class PredictResponse(BaseModel):
    risk_scores: Dict[str, float]
    risk_labels: Dict[str, int]
    risk_level: str
    warning_message: str
    model_name: str
    model_version: str
