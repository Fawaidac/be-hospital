from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal

class VStatistikRawatInapResponse(BaseModel):
    id: int
    type: str
    pelayanan: str
    rawat_inap: str
    klas_perawatan: str
    bulan: int
    tahun: int
    periode: int
    tt: int
    px_awal: int
    px_masuk: int
    px_pindahan: int
    jumlah: int
    px_di_pindahkan: int
    px_keluar_hidup: int
    px_mati: int
    kurang_48_jam: int
    lebih_48_jam: int
    jumlah_keluar: int
    lama_dirawat: int
    px_keluar_m_hr_sama: int
    hari_perawatan: int
    px_akhir: int
    kunjungan: int
    o: Optional[Decimal] = None
    bor: Optional[Decimal] = None
    los: Optional[Decimal] = None
    toi: Optional[Decimal] = None
    bto: Optional[Decimal] = None

    class Config:
        from_attributes = True

class VRekapPelayananResponse(BaseModel):
    type: Optional[str] = None
    pelayanan: str
    bulan: int
    tahun: int
    periode: int
    total_tt: int
    total_px_awal: int
    total_px_masuk: int
    total_px_pindahan: int
    total_jumlah: int
    total_px_di_pindahkan: int
    total_px_keluar_hidup: int
    total_px_mati: int
    total_kurang_48_jam: int
    total_lebih_48_jam: int
    total_jumlah_keluar: int
    total_lama_dirawat: int
    total_px_keluar_m_hr_sama: int
    total_hari_perawatan: int
    total_px_akhir: int
    total_kunjungan: int
    total_o: Optional[Decimal] = None
    total_bor: Optional[Decimal] = None
    total_los: Optional[Decimal] = None
    total_toi: Optional[Decimal] = None
    total_bto: Optional[Decimal] = None

    class Config:
        from_attributes = True

class LaporanGabunganResponse(BaseModel):
    detail: List[VStatistikRawatInapResponse]
    rekap: List[VRekapPelayananResponse]

    class Config:
        from_attributes = True