from pydantic import BaseModel
from typing import List, Optional

class GrandTotalKunjunganItem(BaseModel):
    bulan: int
    tahun: int
    
    # Rawat Jalan
    rawat_jalan_l: int
    rawat_jalan_p: int
    rawat_jalan_total: int
    
    # Rawat Inap (Dari kolom pasien_keluar / kunjungan ranap)
    rawat_inap_l: int
    rawat_inap_p: int
    rawat_inap_total: int
    
    # Gangguan Jiwa
    gangguan_jiwa_l: int
    gangguan_jiwa_p: int
    gangguan_jiwa_total: int
    
    # Kunjungan Gabungan (Ujung Kanan) = RJ + RI + GJ
    kunjungan_grand_total: int

    class Config:
        from_attributes = True


class GrandTotalKunjunganTotal(BaseModel):
    tahun: int
    rawat_jalan_l: int
    rawat_jalan_p: int
    rawat_jalan_total: int
    
    rawat_inap_l: int
    rawat_inap_p: int
    rawat_inap_total: int
    
    gangguan_jiwa_l: int
    gangguan_jiwa_p: int
    gangguan_jiwa_total: int
    
    # Total Seluruh Kunjungan RS Setahun
    kunjungan_grand_total: int


class GrandTotalKunjunganResponse(BaseModel):
    data: List[GrandTotalKunjunganItem]
    total: Optional[GrandTotalKunjunganTotal] = None