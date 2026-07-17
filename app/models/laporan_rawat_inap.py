from sqlalchemy import Column, Integer, DateTime, Numeric
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.sql import func
from app.core.database import BaseMain

class LaporanRawatInapModel(BaseMain):
    __tablename__ = "laporan_rawat_inap"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tahun = Column(Integer, nullable=False)
    bulan = Column(TINYINT, nullable=False)
    jumlah_tempat_tidur = Column(Integer, nullable=False, default=0)
    
    pasien_awal = Column(Integer, nullable=False, default=0)
    pasien_masuk = Column(Integer, nullable=False, default=0)
    pasien_pindahan = Column(Integer, nullable=False, default=0)
    pasien_dipindahkan = Column(Integer, nullable=False, default=0)
    
    pasien_hidup_l = Column(Integer, nullable=False, default=0)
    pasien_hidup_p = Column(Integer, nullable=False, default=0)
    
    pasien_mati_kurang_48jam_l = Column(Integer, nullable=False, default=0)
    pasien_mati_kurang_48jam_p = Column(Integer, nullable=False, default=0)
    
    pasien_mati_lebih_48jam_l = Column(Integer, nullable=False, default=0)
    pasien_mati_lebih_48jam_p = Column(Integer, nullable=False, default=0)
    
    lama_dirawat = Column(Integer, nullable=False, default=0)
    pasien_keluar_mati_hari_sama = Column(Integer, nullable=False, default=0)
    jumlah_hari_rawat = Column(Integer, nullable=False, default=0)
    
    kematian_ibu_hamil = Column(Integer, nullable=False, default=0)
    kematian_ibu_melahirkan = Column(Integer, nullable=False, default=0)
    kematian_ibu_nifas = Column(Integer, nullable=False, default=0)
    kematian_bayi = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class VIndikatorPelayananLengkapModel(BaseMain):
    __tablename__ = "v_indikator_pelayanan_lengkap"

    id = Column(Integer, primary_key=True)
    tahun = Column(Integer, nullable=False)
    bulan = Column(TINYINT, nullable=False)
    jumlah_tempat_tidur = Column(Integer, nullable=False)
    
    pasien_awal = Column(Integer)
    pasien_masuk = Column(Integer)
    pasien_pindahan = Column(Integer)
    pasien_dipindahkan = Column(Integer)
    
    pasien_hidup_l = Column(Integer)
    pasien_hidup_p = Column(Integer)
    pasien_keluar_hidup = Column(Integer) 
    
    pasien_mati_kurang_48jam_l = Column(Integer)
    pasien_mati_kurang_48jam_p = Column(Integer)
    pasien_mati_kurang_48 = Column(Integer) 
    
    pasien_mati_lebih_48jam_l = Column(Integer)
    pasien_mati_lebih_48jam_p = Column(Integer)
    pasien_mati_lebih_48 = Column(Integer) 
    
    lama_dirawat = Column(Integer)
    pasien_keluar_mati_hari_sama = Column(Integer)
    jumlah_hari_rawat = Column(Integer)
    period = Column(Integer) 

    jumlah_pasien_dikelola = Column(Integer) 
    jumlah_pasien_mati = Column(Integer) 
    pasien_akhir = Column(Integer)
    kunjungan = Column(Integer) 
    
    o_pasien_per_hari = Column(Numeric(10, 2)) 
    bor = Column(Numeric(10, 2)) 
    los = Column(Numeric(10, 2)) 
    toi = Column(Numeric(10, 2)) 
    bto = Column(Numeric(10, 2))
    
    kematian_ibu_hamil = Column(Integer)
    kematian_ibu_melahirkan = Column(Integer)
    kematian_ibu_nifas = Column(Integer)
    kematian_bayi = Column(Integer)