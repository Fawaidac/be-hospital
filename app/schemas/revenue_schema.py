from pydantic import BaseModel, Field
from typing import List, Optional

class TargetInput(BaseModel):
    category_code: str
    target_tahunan: float
    target_bulanan: float

class CategoryAmountInput(BaseModel):
    category_code: str
    amount: float

class RealisasiInput(BaseModel):
    bulan: int = Field(..., ge=1, le=12)
    categories: List[CategoryAmountInput]

class RevenueStoreRequest(BaseModel):
    tahun: int
    targets: List[TargetInput]
    realisasi: Optional[List[RealisasiInput]] = None