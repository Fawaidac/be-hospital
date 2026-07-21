from sqlalchemy import Column, Float, Integer, String, SmallInteger, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import BaseMain

class KelompokPelayananModel(BaseMain):
    __tablename__ = "kelompok_pelayanan"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nama = Column(String(100), nullable=False, unique=True)
    
    # Relationships
    ruangan = relationship("RuanganModel", back_populates="kelompok")

class RuanganModel(BaseMain):
    __tablename__ = "ruangan"
    id = Column(Integer, primary_key=True, autoincrement=True)
    kelompok_id = Column(Integer, ForeignKey("kelompok_pelayanan.id"), nullable=False)
    nama = Column(String(100), nullable=False) 
    urutan = Column(Integer, default=0)
    
    # Relationships
    kelompok = relationship("KelompokPelayananModel", back_populates="ruangan")
    statistik = relationship("StatistikRawatInapModel", back_populates="ruangan")

class KelasPerawatanModel(BaseMain):
    __tablename__ = "kelas_perawatan"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nama = Column(String(50), nullable=False, unique=True)
    
    # Relationships
    statistik = relationship("StatistikRawatInapModel", back_populates="kelas")

class PeriodeModel(BaseMain):
    __tablename__ = "periode"
    id = Column(Integer, primary_key=True, autoincrement=True)
    bulan = Column(Integer, nullable=False) # Disesuaikan INT di DB
    tahun = Column(Integer, nullable=False)
    hari = Column(Integer, nullable=False) # Ditambahkan kolom hari sesuai DB
    
    # Relationships
    statistik = relationship("StatistikRawatInapModel", back_populates="periode")

class StatistikRawatInapModel(BaseMain):
    __tablename__ = "statistik_rawat_inap"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ruangan_id = Column(Integer, ForeignKey("ruangan.id"), nullable=True)
    kelas_id = Column(Integer, ForeignKey("kelas_perawatan.id"), nullable=True) # Mendukung NULL untuk RICU ED ke-2
    periode_id = Column(Integer, ForeignKey("periode.id"), nullable=True)
    tipe = Column(String(100), nullable=True)
    tempat_tidur = Column(Integer, nullable=True)
    px_awal = Column(Integer, nullable=True)
    px_masuk = Column(Integer, nullable=True)
    px_pindahan_masuk = Column(Integer, nullable=True)
    px_dipindahkan = Column(Integer, nullable=True)
    px_keluar_hidup = Column(Integer, nullable=True)
    px_mati = Column(Integer, nullable=True)
    px_mati_kurang_48jam = Column(Integer, nullable=True)
    px_mati_lebih_48jam = Column(Integer, nullable=True)
    lama_dirawat = Column(Integer, nullable=True)
    px_keluar_meninggal_hr_sama = Column(Integer, nullable=True)
    hari_perawatan = Column(Integer, nullable=True)
    px_akhir = Column(Integer, nullable=True)
    kunjungan = Column(Integer, nullable=True)

    # Indikator Barber-Johnson menggunakan Float atau Numeric
    bor = Column(Numeric(10, 2), nullable=True)
    los = Column(Numeric(10, 2), nullable=True)
    toi = Column(Numeric(10, 2), nullable=True)
    bto = Column(Numeric(10, 2), nullable=True)

    # Relationships
    ruangan = relationship("RuanganModel", back_populates="statistik")
    kelas = relationship("KelasPerawatanModel", back_populates="statistik")
    periode = relationship("PeriodeModel", back_populates="statistik")


class VStatistikRawatInap(BaseMain):
    """Mapping dari database View v_statistik_rawat_inap untuk mempermudah Query"""
    __tablename__ = "v_statistik_rawat_inap"
    
    # primary_key=True dipasang fiktif agar SQLAlchemy tidak error membaca View
    id = Column(Integer, primary_key=True)
    type = Column(String(100), nullable=False)
    pelayanan = Column(String(100), primary_key=True) 
    rawat_inap = Column(String(100), primary_key=True)
    klas_perawatan = Column(String(50))
    bulan = Column(Integer, primary_key=True)  
    tahun = Column(Integer, primary_key=True)  
    periode = Column(Integer)
    tt = Column(Integer)
    px_awal = Column(Integer)
    px_masuk = Column(Integer)
    px_pindahan = Column(Integer)
    jumlah = Column(Integer)
    px_di_pindahkan = Column(Integer)
    px_keluar_hidup = Column(Integer)
    px_mati = Column(Integer)
    kurang_48_jam = Column(Integer)
    lebih_48_jam = Column(Integer)
    jumlah_keluar = Column(Integer)
    lama_dirawat = Column(Integer)
    px_keluar_m_hr_sama = Column(Integer)
    hari_perawatan = Column(Integer)
    px_akhir = Column(Integer)
    kunjungan = Column(Integer)
    o = Column(Numeric(10, 2))
    bor = Column(Numeric(10, 2))
    los = Column(Numeric(10, 2))
    toi = Column(Numeric(10, 2))
    bto = Column(Numeric(10, 2))


class VRekapPelayanan(BaseMain):
    """Mapping dari database View v_rekap_pelayanan untuk mempermudah Query"""
    __tablename__ = "v_rekap_pelayanan"
    
    type = Column(String(100), primary_key=True)
    pelayanan = Column(String(100), primary_key=True)
    bulan = Column(Integer, primary_key=True)
    tahun = Column(Integer, primary_key=True)
    periode = Column(Integer)
    total_tt = Column(Integer)
    total_px_awal = Column(Integer)
    total_px_masuk = Column(Integer)
    total_px_pindahan = Column(Integer)
    total_jumlah = Column(Integer)
    total_px_di_pindahkan = Column(Integer)
    total_px_keluar_hidup = Column(Integer)
    total_px_mati = Column(Integer)
    total_kurang_48_jam = Column(Integer)
    total_lebih_48_jam = Column(Integer)
    total_jumlah_keluar = Column(Integer)
    total_lama_dirawat = Column(Integer)
    total_px_keluar_m_hr_sama = Column(Integer)
    total_hari_perawatan = Column(Integer)
    total_px_akhir = Column(Integer)
    total_kunjungan = Column(Integer)
    total_o = Column(Numeric(10, 2))
    total_bor = Column(Numeric(10, 2))
    total_los = Column(Numeric(10, 2))
    total_toi = Column(Numeric(10, 2))
    total_bto = Column(Numeric(10, 2))