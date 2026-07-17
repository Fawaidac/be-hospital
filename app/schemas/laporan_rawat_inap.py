from pydantic import BaseModel, Field, model_validator
from typing import List, Optional
from datetime import datetime

# =========================================================
# BASE SCHEMA (Menampung Kolom Dasar/Mentah Input DB)
# =========================================================
class LaporanRawatInapBase(BaseModel):
    tahun: int
    bulan: int = Field(..., ge=1, le=12)
    jumlah_tempat_tidur: int = Field(default=0, ge=0)
    
    # Pergerakan Pasien (Data Mentah)
    pasien_awal: int = Field(default=0, ge=0)
    pasien_masuk: int = Field(default=0, ge=0)
    pasien_pindahan: int = Field(default=0, ge=0)
    pasien_dipindahkan: int = Field(default=0, ge=0)
    
    # Breakdown Pasien Hidup & Mati
    pasien_hidup_l: int = Field(default=0, ge=0)
    pasien_hidup_p: int = Field(default=0, ge=0)
    pasien_mati_kurang_48jam_l: int = Field(default=0, ge=0)
    pasien_mati_kurang_48jam_p: int = Field(default=0, ge=0)
    pasien_mati_lebih_48jam_l: int = Field(default=0, ge=0)
    pasien_mati_lebih_48jam_p: int = Field(default=0, ge=0)
    
    # Logistik Perawatan
    lama_dirawat: int = Field(default=0, ge=0)
    pasien_keluar_mati_hari_sama: int = Field(default=0, ge=0)
    jumlah_hari_rawat: int = Field(default=0, ge=0)
    
    # Kematian Ibu & Bayi
    kematian_ibu_hamil: int = Field(default=0, ge=0)
    kematian_ibu_melahirkan: int = Field(default=0, ge=0)
    kematian_ibu_nifas: int = Field(default=0, ge=0)
    kematian_bayi: int = Field(default=0, ge=0)


class LaporanRawatInapCreate(LaporanRawatInapBase):
    pass


class LaporanRawatInapUpdate(BaseModel):
    tahun: Optional[int] = None
    bulan: Optional[int] = Field(default=None, ge=1, le=12)
    jumlah_tempat_tidur: Optional[int] = Field(default=None, ge=0)
    pasien_awal: Optional[int] = Field(default=None, ge=0)
    pasien_masuk: Optional[int] = Field(default=None, ge=0)
    pasien_pindahan: Optional[int] = Field(default=None, ge=0)
    pasien_dipindahkan: Optional[int] = Field(default=None, ge=0)
    pasien_hidup_l: Optional[int] = Field(default=None, ge=0)
    pasien_hidup_p: Optional[int] = Field(default=None, ge=0)
    pasien_mati_kurang_48jam_l: Optional[int] = Field(default=None, ge=0)
    pasien_mati_kurang_48jam_p: Optional[int] = Field(default=None, ge=0)
    pasien_mati_lebih_48jam_l: Optional[int] = Field(default=None, ge=0)
    pasien_mati_lebih_48jam_p: Optional[int] = Field(default=None, ge=0)
    lama_dirawat: Optional[int] = Field(default=None, ge=0)
    pasien_keluar_mati_hari_sama: Optional[int] = Field(default=None, ge=0)
    jumlah_hari_rawat: Optional[int] = Field(default=None, ge=0)
    kematian_ibu_hamil: Optional[int] = Field(default=None, ge=0)
    kematian_ibu_melahirkan: Optional[int] = Field(default=None, ge=0)
    kematian_ibu_nifas: Optional[int] = Field(default=None, ge=0)
    kematian_bayi: Optional[int] = Field(default=None, ge=0)


class LaporanRawatInapResponse(LaporanRawatInapBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =========================================================
# RESPONSE SCHEMA UNTUK GET ALL INDIKATOR KINERJA LENGKAP
# =========================================================
class VIndikatorKinerjaResponse(BaseModel):
    id: int
    tahun: int
    bulan: int
    jumlah_tempat_tidur: int
    
    pasien_awal: int
    pasien_masuk: int
    pasien_pindahan: int
    pasien_dipindahkan: int
    
    pasien_hidup_l: int
    pasien_hidup_p: int
    pasien_keluar_hidup: int
    
    pasien_mati_kurang_48jam_l: int
    pasien_mati_kurang_48jam_p: int
    pasien_mati_kurang_48: int
    
    pasien_mati_lebih_48jam_l: int
    pasien_mati_lebih_48jam_p: int
    pasien_mati_lebih_48: int
    
    lama_dirawat: int
    pasien_keluar_mati_hari_sama: int
    jumlah_hari_rawat: int
    period: Optional[int] = None
    
    jumlah_pasien_dikelola: int
    jumlah_pasien_mati: int
    pasien_akhir: int
    kunjungan: int
    
    o_pasien_per_hari: Optional[float] = None
    bor: Optional[float] = None
    los_dinkes: Optional[float] = Field(None, validation_alias="los")
    los_bbj: Optional[float] = None
    toi: Optional[float] = None
    bto: Optional[float] = None
    
    kematian_ibu_hamil: int
    kematian_ibu_melahirkan: int
    kematian_ibu_nifas: int
    kematian_bayi: int

    @model_validator(mode="before")
    @classmethod
    def calculate_los_bbj(cls, data):
        if not isinstance(data, dict):
            hari_rawat = getattr(data, "jumlah_hari_rawat", 0)
            kunjungan = getattr(data, "kunjungan", 0)
            if kunjungan and kunjungan > 0:
                data.los_bbj = round(hari_rawat / kunjungan, 2)
        else:
            hari_rawat = data.get("jumlah_hari_rawat", 0)
            kunjungan = data.get("kunjungan", 0)
            if kunjungan and kunjungan > 0:
                data["los_bbj"] = round(hari_rawat / kunjungan, 2)
        return data

    class Config:
        from_attributes = True
        populate_by_name = True


# =========================================================
# BULK & LIST RESPONSE
# =========================================================
class LaporanRawatInapItem(BaseModel):
    bulan: int = Field(..., ge=1, le=12)
    jumlah_tempat_tidur: int = Field(default=0, ge=0)
    pasien_awal: int = Field(default=0, ge=0)
    pasien_masuk: int = Field(default=0, ge=0)
    pasien_pindahan: int = Field(default=0, ge=0)
    pasien_dipindahkan: int = Field(default=0, ge=0)
    pasien_hidup_l: int = Field(default=0, ge=0)
    pasien_hidup_p: int = Field(default=0, ge=0)
    pasien_mati_kurang_48jam_l: int = Field(default=0, ge=0)
    pasien_mati_kurang_48jam_p: int = Field(default=0, ge=0)
    pasien_mati_lebih_48jam_l: int = Field(default=0, ge=0)
    pasien_mati_lebih_48jam_p: int = Field(default=0, ge=0)
    lama_dirawat: int = Field(default=0, ge=0)
    pasien_keluar_mati_hari_sama: int = Field(default=0, ge=0)
    jumlah_hari_rawat: int = Field(default=0, ge=0)
    kematian_ibu_hamil: int = Field(default=0, ge=0)
    kematian_ibu_melahirkan: int = Field(default=0, ge=0)
    kematian_ibu_nifas: int = Field(default=0, ge=0)
    kematian_bayi: int = Field(default=0, ge=0)


class LaporanRawatInapBulkCreate(BaseModel):
    tahun: int
    data: List[LaporanRawatInapItem]


class LaporanRawatInapTotalResponse(BaseModel):
    tahun: int
    jumlah_tempat_tidur: float
    pasien_awal: int
    pasien_masuk: int
    pasien_pindahan: int
    pasien_dipindahkan: int
    pasien_hidup_total: int
    pasien_mati_kurang_48jam_total: int
    pasien_mati_lebih_48jam_total: int
    pasien_keluar_mati_total: int
    total_kunjungan_total: int
    jumlah_hari_rawat: int
    lama_dirawat: int
    pasien_keluar_mati_hari_sama: int
    pasien_akhir: int
    
    bor: Optional[float] = None
    los_dinkes: Optional[float] = None
    los_bbj: Optional[float] = None
    toi: Optional[float] = None
    bto: Optional[float] = None
    gdr_total: Optional[float] = None
    ndr_total: Optional[float] = None
    
    kematian_ibu_hamil: int
    kematian_ibu_melahirkan: int
    kematian_ibu_nifas: int
    kematian_bayi: int


class LaporanRawatInapListResponse(BaseModel):
    data: List[VIndikatorKinerjaResponse]
    total: Optional[LaporanRawatInapTotalResponse] = None

# =========================================================
# SCHEMA KHUSUS NDR GDR (Disesuaikan dengan Model Baru)
# =========================================================
class NDRGDRItemResponse(BaseModel):
    id: int
    tahun: int
    bulan: int
    pasien_hidup_l: int
    pasien_hidup_p: int
    pasien_hidup_total: int = Field(validation_alias="pasien_keluar_hidup")
    pasien_mati_kurang_48jam_l: int
    pasien_mati_kurang_48jam_p: int
    pasien_mati_kurang_48jam_total: int = Field(validation_alias="pasien_mati_kurang_48")
    pasien_mati_lebih_48jam_l: int
    pasien_mati_lebih_48jam_p: int
    pasien_mati_lebih_48jam_total: int = Field(validation_alias="pasien_mati_lebih_48")
    pasien_keluar_mati_l: int = Field(default=0, validation_alias="pasien_mati_kurang_48jam_l") 
    pasien_keluar_mati_p: int = Field(default=0, validation_alias="pasien_mati_kurang_48jam_p")
    pasien_keluar_mati_total: int = Field(validation_alias="jumlah_pasien_mati")
    total_kunjungan_l: int = Field(default=0, validation_alias="pasien_hidup_l")
    total_kunjungan_p: int = Field(default=0, validation_alias="pasien_hidup_p")
    total_kunjungan_total: int = Field(validation_alias="kunjungan")
    gdr_l: Optional[float] = None
    gdr_p: Optional[float] = None
    gdr_total: Optional[float] = None
    ndr_l: Optional[float] = None
    ndr_p: Optional[float] = None
    ndr_total: Optional[float] = None

    class Config:
        from_attributes = True
        populate_by_name = True

class NDRGDRTotalResponse(BaseModel):
    tahun: int
    pasien_hidup_l: int
    pasien_hidup_p: int
    pasien_hidup_total: int
    pasien_mati_kurang_48jam_l: int
    pasien_mati_kurang_48jam_p: int
    pasien_mati_kurang_48jam_total: int
    pasien_mati_lebih_48jam_l: int
    pasien_mati_lebih_48jam_p: int
    pasien_mati_lebih_48jam_total: int
    pasien_keluar_mati_l: int
    pasien_keluar_mati_p: int
    pasien_keluar_mati_total: int
    total_kunjungan_l: int
    total_kunjungan_p: int
    total_kunjungan_total: int
    gdr_l: Optional[float] = None
    gdr_p: Optional[float] = None
    gdr_total: Optional[float] = None
    ndr_l: Optional[float] = None
    ndr_p: Optional[float] = None
    ndr_total: Optional[float] = None


class NDRGDRListResponse(BaseModel):
    data: List[NDRGDRItemResponse]
    total: Optional[NDRGDRTotalResponse] = None

class SensusRanapLengkapItem(BaseModel):
    bulan: int
    tahun: int
    period: int
    jumlah_tempat_tidur: int
    pasien_awal: int
    pasien_masuk: int
    pasien_pindahan: int
    jumlah_pasien_dikelola: int  # Kolom 4: (1+2+3)
    pasien_dipindahkan: int      # Kolom 5
    pasien_keluar_hidup: int     # Kolom 6
    pasien_mati_kurang_48: int   # Kolom 8
    pasien_mati_lebih_48: int    # Kolom 9
    jumlah_pasien_mati: int      # Kolom 10: (5+6+7)
    lama_dirawat: int            # Kolom 11
    pasien_keluar_mati_hari_sama: int # Kolom 12
    jumlah_hari_rawat: int       # Kolom 13
    pasien_akhir: int            # Kolom 14
    kunjungan: int           # Kunjungan (Kanan)
    o_pasien_per_hari: Optional[float] = None # Kolom 15
    bor: Optional[float] = None  # Kolom 16
    los: Optional[float] = None  # Kolom 17
    toi: Optional[float] = None  # Kolom 18
    bto: Optional[float] = None  # Kolom 19

    class Config:
        from_attributes = True


class SensusRanapLengkapTotal(BaseModel):
    tahun: int
    period: int
    jumlah_tempat_tidur: float
    pasien_awal: int
    pasien_masuk: int
    pasien_pindahan: int
    jumlah_pasien_dikelola: int
    pasien_dipindahkan: int
    pasien_keluar_hidup: int
    pasien_mati_kurang_48jam_total: int
    pasien_mati_lebih_48jam_total: int
    jumlah_pasien_mati: int
    lama_dirawat: int
    pasien_keluar_mati_hari_sama: int
    jumlah_hari_rawat: int
    pasien_akhir: int
    kunjungan: int
    o_pasien_per_hari: Optional[float] = None
    bor: Optional[float] = None
    los: Optional[float] = None
    toi: Optional[float] = None
    bto: Optional[float] = None


class SensusRanapLengkapResponse(BaseModel):
    data: List[SensusRanapLengkapItem]
    total: Optional[SensusRanapLengkapTotal] = None