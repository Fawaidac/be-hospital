from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from sqlalchemy import func
from app.models.laporan_rawat_inap import LaporanRawatInapModel, VIndikatorPelayananLengkapModel
from app.schemas.laporan_rawat_inap import LaporanRawatInapBulkCreate, LaporanRawatInapCreate, LaporanRawatInapUpdate


class LaporanRawatInapService:
    @staticmethod
    def get_all(db: Session, tahun: int):
        items = (
            db.query(VIndikatorPelayananLengkapModel)
            .filter(VIndikatorPelayananLengkapModel.tahun == tahun)
            .order_by(VIndikatorPelayananLengkapModel.bulan.asc())
            .all()
        )
        total = LaporanRawatInapService._calculate_total(db, tahun)
        return {"data": items, "total": total}

    @staticmethod
    def _calculate_total(db: Session, tahun: int):
        row = (
            db.query(
                # Agregasi Data Mentah Pergerakan Pasien
                func.sum(LaporanRawatInapModel.pasien_awal).label("total_pasien_awal"),
                func.sum(LaporanRawatInapModel.pasien_masuk).label("total_pasien_masuk"),
                func.sum(LaporanRawatInapModel.pasien_pindahan).label("total_pasien_pindahan"),
                func.sum(LaporanRawatInapModel.pasien_dipindahkan).label("total_pasien_dipindahkan"),
                func.sum(LaporanRawatInapModel.pasien_keluar_mati_hari_sama).label("total_mati_hari_sama"),

                # Agregasi Pasien Keluar Hidup
                func.sum(LaporanRawatInapModel.pasien_hidup_l).label("total_hidup_l"),
                func.sum(LaporanRawatInapModel.pasien_hidup_p).label("total_hidup_p"),
                
                # Agregasi Pasien Mati < 48 Jam
                func.sum(LaporanRawatInapModel.pasien_mati_kurang_48jam_l).label("total_mati_kurang_l"),
                func.sum(LaporanRawatInapModel.pasien_mati_kurang_48jam_p).label("total_mati_kurang_p"),
                
                # Agregasi Pasien Mati >= 48 Jam
                func.sum(LaporanRawatInapModel.pasien_mati_lebih_48jam_l).label("total_mati_lebih_l"),
                func.sum(LaporanRawatInapModel.pasien_mati_lebih_48jam_p).label("total_mati_lebih_p"),
                
                # Logistik Perawatan & Tambahan Kematian Ibu/Bayi
                func.sum(LaporanRawatInapModel.jumlah_hari_rawat).label("total_jumlah_hari_rawat"),
                func.sum(LaporanRawatInapModel.lama_dirawat).label("total_lama_dirawat"),
                func.sum(LaporanRawatInapModel.kematian_ibu_hamil).label("total_ibu_hamil"),
                func.sum(LaporanRawatInapModel.kematian_ibu_melahirkan).label("total_ibu_melahirkan"),
                func.sum(LaporanRawatInapModel.kematian_ibu_nifas).label("total_ibu_nifas"),
                func.sum(LaporanRawatInapModel.kematian_bayi).label("total_kematian_bayi"),

                func.avg(func.nullif(LaporanRawatInapModel.jumlah_tempat_tidur, 0)).label("rata_tempat_tidur"),
                func.sum(
                    func.if_(
                        LaporanRawatInapModel.jumlah_tempat_tidur > 0,
                        func.day(func.last_day(
                            func.str_to_date(func.concat(LaporanRawatInapModel.tahun, '-', LaporanRawatInapModel.bulan, '-01'), '%Y-%m-%d')
                        )),
                        0
                    )
                ).label("total_hari_dalam_setahun"),
            )
            .filter(LaporanRawatInapModel.tahun == tahun)
            .filter(LaporanRawatInapModel.jumlah_tempat_tidur > 0)
            .first()
        )

        if not row or row.total_jumlah_hari_rawat is None:
            return None

        # Parsing data dasar L dan P
        hidup_l = int(row.total_hidup_l or 0)
        hidup_p = int(row.total_hidup_p or 0)
        hidup_total = hidup_l + hidup_p

        kurang_48_l = int(row.total_mati_kurang_l or 0)
        kurang_48_p = int(row.total_mati_kurang_p or 0)
        kurang_48_total = kurang_48_l + kurang_48_p

        lebih_48_l = int(row.total_mati_lebih_l or 0)
        lebih_48_p = int(row.total_mati_lebih_p or 0)
        lebih_48_total = lebih_48_l + lebih_48_p

        mati_l = kurang_48_l + lebih_48_l
        mati_p = kurang_48_p + lebih_48_p
        mati_total = mati_l + mati_p

        kunjungan_l = hidup_l + mati_l
        kunjungan_p = hidup_p + mati_p
        kunjungan_total = kunjungan_l + kunjungan_p

        bed = float(row.rata_tempat_tidur or 0)
        hari_total = int(row.total_hari_dalam_setahun or 0)
        hari_rawat = int(row.total_jumlah_hari_rawat or 0)
        lama_dirawat = int(row.total_lama_dirawat or 0)

        # Hitung Indikator Utama (BOR, LOS, TOI, BTO)
        bor = round((hari_rawat / (bed * hari_total)) * 100, 2) if bed and hari_total else None
        los_dinkes = round(lama_dirawat / kunjungan_total, 2) if kunjungan_total else None
        los_bbj = round(hari_rawat / kunjungan_total, 2) if kunjungan_total else None
        toi = round(((bed * hari_total) - hari_rawat) / kunjungan_total, 2) if kunjungan_total else None
        bto = round(kunjungan_total / bed, 2) if bed else None

        # Kalkulasi NDR & GDR Tahunan lengkap (‰)
        gdr_l = round((mati_l / kunjungan_l) * 1000, 2) if kunjungan_l else None
        gdr_p = round((mati_p / kunjungan_p) * 1000, 2) if kunjungan_p else None
        gdr_total = round((mati_total / kunjungan_total) * 1000, 2) if kunjungan_total else None

        ndr_l = round((lebih_48_l / kunjungan_l) * 1000, 2) if kunjungan_l else None
        ndr_p = round((lebih_48_p / kunjungan_p) * 1000, 2) if kunjungan_p else None
        ndr_total = round((lebih_48_total / kunjungan_total) * 1000, 2) if kunjungan_total else None

        # Hitung Akumulasi Akhir Pasien Akhir (Kolom 14)
        pasien_akhir = (int(row.total_pasien_awal or 0) + int(row.total_pasien_masuk or 0) + int(row.total_pasien_pindahan or 0)) - \
                        (int(row.total_pasien_dipindahkan or 0) + hidup_total + mati_total)

        return {
            "tahun": tahun,
            "jumlah_tempat_tidur": bed,
            "pasien_awal": int(row.total_pasien_awal or 0),
            "pasien_masuk": int(row.total_pasien_masuk or 0),
            "pasien_pindahan": int(row.total_pasien_pindahan or 0),
            "pasien_dipindahkan": int(row.total_pasien_dipindahkan or 0),
            "pasien_hidup_l": hidup_l,
            "pasien_hidup_p": hidup_p,
            "pasien_hidup_total": hidup_total,
            "pasien_mati_kurang_48jam_l": kurang_48_l,
            "pasien_mati_kurang_48jam_p": kurang_48_p,
            "pasien_mati_kurang_48jam_total": kurang_48_total,
            "pasien_mati_lebih_48jam_l": lebih_48_l,
            "pasien_mati_lebih_48jam_p": lebih_48_p,
            "pasien_mati_lebih_48jam_total": lebih_48_total,
            "pasien_keluar_mati_l": mati_l,
            "pasien_keluar_mati_p": mati_p,
            "pasien_keluar_mati_total": mati_total,
            "total_kunjungan_l": kunjungan_l,
            "total_kunjungan_p": kunjungan_p,
            "total_kunjungan_total": kunjungan_total,
            "jumlah_hari_rawat": hari_rawat,
            "lama_dirawat": lama_dirawat,
            "pasien_keluar_mati_hari_sama": int(row.total_mati_hari_sama or 0),
            "pasien_akhir": pasien_akhir,
            "bor": bor,
            "los_dinkes": los_dinkes,
            "los_bbj": los_bbj,
            "toi": toi,
            "bto": bto,
            "gdr_l": gdr_l,
            "gdr_p": gdr_p,
            "gdr_total": gdr_total,
            "ndr_l": ndr_l,
            "ndr_p": ndr_p,
            "ndr_total": ndr_total,
            "kematian_ibu_hamil": int(row.total_ibu_hamil or 0),
            "kematian_ibu_melahirkan": int(row.total_ibu_melahirkan or 0),
            "kematian_ibu_nifas": int(row.total_ibu_nifas or 0),
            "kematian_bayi": int(row.total_kematian_bayi or 0),
        }

    @staticmethod
    def get_by_id(db: Session, id: int):
        item = db.query(VIndikatorPelayananLengkapModel).filter(VIndikatorPelayananLengkapModel.id == id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Laporan rawat inap tidak ditemukan")
        return item

    @staticmethod
    def create(db: Session, payload: LaporanRawatInapCreate):
        existing = db.query(LaporanRawatInapModel).filter(
            LaporanRawatInapModel.tahun == payload.tahun,
            LaporanRawatInapModel.bulan == payload.bulan
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Laporan rawat inap untuk tahun {payload.tahun} bulan {payload.bulan} sudah ada."
            )

        db_item = LaporanRawatInapModel(**payload.model_dump())
        db.add(db_item)
        try:
            db.commit()
            db.refresh(db_item)
            return db.query(VIndikatorPelayananLengkapModel).filter(VIndikatorPelayananLengkapModel.id == db_item.id).first()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=400, detail="Terjadi kesalahan integritas data.")

    @staticmethod
    def update(db: Session, id: int, payload: LaporanRawatInapUpdate):
        db_item = db.query(LaporanRawatInapModel).filter(LaporanRawatInapModel.id == id).first()
        if not db_item:
            raise HTTPException(status_code=404, detail="Laporan rawat inap tidak ditemukan")

        update_data = payload.model_dump(exclude_unset=True)

        new_tahun = update_data.get("tahun", db_item.tahun)
        new_bulan = update_data.get("bulan", db_item.bulan)
        if new_tahun != db_item.tahun or new_bulan != db_item.bulan:
            existing = db.query(LaporanRawatInapModel).filter(
                LaporanRawatInapModel.tahun == new_tahun,
                LaporanRawatInapModel.bulan == new_bulan,
                LaporanRawatInapModel.id != id
            ).first()
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Laporan rawat inap untuk tahun {new_tahun} bulan {new_bulan} sudah ada."
                )

        for key, value in update_data.items():
            setattr(db_item, key, value)

        try:
            db.commit()
            db.refresh(db_item)
            return db.query(VIndikatorPelayananLengkapModel).filter(VIndikatorPelayananLengkapModel.id == db_item.id).first()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=400, detail="Terjadi kesalahan integritas data.")

    @staticmethod
    def delete(db: Session, id: int):
        db_item = db.query(LaporanRawatInapModel).filter(LaporanRawatInapModel.id == id).first()
        if not db_item:
            raise HTTPException(status_code=404, detail="Laporan rawat inap tidak ditemukan")
        db.delete(db_item)
        db.commit()
        return True
    
    @staticmethod
    def create_bulk(db: Session, payload: LaporanRawatInapBulkCreate):
        tahun = payload.tahun
        bulan_list = [item.bulan for item in payload.data]

        if len(bulan_list) != len(set(bulan_list)):
            raise HTTPException(status_code=400, detail="Terdapat bulan duplikat dalam data yang dikirim.")

        existing = db.query(LaporanRawatInapModel).filter(
            LaporanRawatInapModel.tahun == tahun,
            LaporanRawatInapModel.bulan.in_(bulan_list)
        ).all()
        if existing:
            bulan_existing = [item.bulan for item in existing]
            raise HTTPException(
                status_code=400,
                detail=f"Data tahun {tahun} untuk bulan {bulan_existing} sudah ada."
            )

        db_items = [
            LaporanRawatInapModel(tahun=tahun, **item.model_dump())
            for item in payload.data
        ]

        try:
            db.add_all(db_items)
            db.commit()
            ids = [item.id for item in db_items]
            return (
                db.query(VIndikatorPelayananLengkapModel)
                .filter(VIndikatorPelayananLengkapModel.id.in_(ids))
                .order_by(VIndikatorPelayananLengkapModel.bulan.asc())
                .all()
            )
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=400, detail="Terjadi kesalahan integritas data.")

    @staticmethod
    def get_total(db: Session, tahun: int):
        total = LaporanRawatInapService._calculate_total(db, tahun)
        if not total:
            raise HTTPException(status_code=404, detail=f"Data tahun {tahun} tidak ditemukan.")
        return total
    
    @staticmethod
    def get_ndr_gdr(db: Session, tahun: int):
        items = (
            db.query(VIndikatorPelayananLengkapModel)
            .filter(VIndikatorPelayananLengkapModel.tahun == tahun)
            .order_by(VIndikatorPelayananLengkapModel.bulan.asc())
            .all()
        )
        
        total_data = LaporanRawatInapService._calculate_total(db, tahun)
        
        total = None
        if total_data:
            total = {
                "tahun": total_data["tahun"],
                "pasien_hidup_l": total_data["pasien_hidup_l"],
                "pasien_hidup_p": total_data["pasien_hidup_p"],
                "pasien_hidup_total": total_data["pasien_hidup_total"],
                "pasien_mati_kurang_48jam_l": total_data["pasien_mati_kurang_48jam_l"],
                "pasien_mati_kurang_48jam_p": total_data["pasien_mati_kurang_48jam_p"],
                "pasien_mati_kurang_48jam_total": total_data["pasien_mati_kurang_48jam_total"],
                "pasien_mati_lebih_48jam_l": total_data["pasien_mati_lebih_48jam_l"],
                "pasien_mati_lebih_48jam_p": total_data["pasien_mati_lebih_48jam_p"],
                "pasien_mati_lebih_48jam_total": total_data["pasien_mati_lebih_48jam_total"],
                "pasien_keluar_mati_l": total_data["pasien_keluar_mati_l"],
                "pasien_keluar_mati_p": total_data["pasien_keluar_mati_p"],
                "pasien_keluar_mati_total": total_data["pasien_keluar_mati_total"],
                "total_kunjungan_l": total_data["total_kunjungan_l"],
                "total_kunjungan_p": total_data["total_kunjungan_p"],
                "total_kunjungan_total": total_data["total_kunjungan_total"],
                "gdr_l": total_data["gdr_l"],
                "gdr_p": total_data["gdr_p"],
                "gdr_total": total_data["gdr_total"],
                "ndr_l": total_data["ndr_l"],
                "ndr_p": total_data["ndr_p"],
                "ndr_total": total_data["ndr_total"]
            }
            
        return {"data": items, "total": total}
    
    @staticmethod
    def get_sensus_lengkap(db: Session, tahun: int):
        # Ambil seluruh records bulanan dari view pelayanan lengkap
        items = (
            db.query(VIndikatorPelayananLengkapModel)
            .filter(VIndikatorPelayananLengkapModel.tahun == tahun)
            .order_by(VIndikatorPelayananLengkapModel.bulan.asc())
            .all()
        )
        
        total_raw = LaporanRawatInapService._calculate_total(db, tahun)
        
        total = None
        if total_raw:
            # Hitung total hari periode (SUM dari kolom period di setiap bulan aktif)
            total_period = sum(int(item.period or 0) for item in items if item.jumlah_tempat_tidur > 0)
            
            # Hitung nilai rata-rata O (Pasien per hari) setahun = total hari rawat / total hari periode aktif
            o_total = round(total_raw["jumlah_hari_rawat"] / total_period, 2) if total_period else None
            
            # Khusus untuk baris total 'PX AWAL' (Kolom 1) diisi nilai bulan pertama yang aktif (Januari)
            # Sedangkan 'PX AKHIR' (Kolom 14) diisi nilai dari bulan terakhir yang aktif (Juni)
            px_awal_riil = items[0].pasien_awal if items else 0
            px_akhir_riil = 0
            for item in reversed(items):
                if item.jumlah_tempat_tidur > 0:
                    px_akhir_riil = item.pasien_akhir
                    break

            total = {
                "tahun": total_raw["tahun"],
                "period": total_period, 
                "jumlah_tempat_tidur": total_raw["jumlah_tempat_tidur"],
                "pasien_awal": px_awal_riil,
                "pasien_masuk": total_raw["pasien_masuk"],
                "pasien_pindahan": total_raw["pasien_pindahan"],
                "jumlah_pasien_dikelola": px_awal_riil + total_raw["pasien_masuk"] + total_raw["pasien_pindahan"],
                "pasien_dipindahkan": total_raw["pasien_dipindahkan"],
                "pasien_keluar_hidup": total_raw["pasien_hidup_total"],
                "pasien_mati_kurang_48jam_total": total_raw["pasien_mati_kurang_48jam_total"],
                "pasien_mati_lebih_48jam_total": total_raw["pasien_mati_lebih_48jam_total"],
                "jumlah_pasien_mati": total_raw["pasien_keluar_mati_total"],
                "lama_dirawat": total_raw["lama_dirawat"],
                "pasien_keluar_mati_hari_sama": total_raw["pasien_keluar_mati_hari_sama"],
                "jumlah_hari_rawat": total_raw["jumlah_hari_rawat"],
                "pasien_akhir": px_akhir_riil,
                
                "kunjungan": total_raw["total_kunjungan_total"], 
                
                "o_pasien_per_hari": o_total,
                "bor": total_raw["bor"],
                "los": total_raw["los"],
                "toi": total_raw["toi"],
                "bto": total_raw["bto"]
            }
            
        return {"data": items, "total": total}