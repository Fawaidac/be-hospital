from sqlalchemy.orm import Session
from app.models.laporan_rawat_inap import VIndikatorPelayananLengkapModel

class LaporanKunjunganService:
    @staticmethod
    def get_grand_total_kunjungan(db: Session, tahun: int):
        # Langsung query dari View pelayanan lengkap, tidak perlu join tabel lain
        query_data = (
            db.query(VIndikatorPelayananLengkapModel)
            .filter(VIndikatorPelayananLengkapModel.tahun == tahun)
            .order_by(VIndikatorPelayananLengkapModel.bulan.asc())
            .all()
        )

        items = []
        # Total akumulator untuk baris paling bawah tabel
        tot_rj_l = tot_rj_p = tot_rj_t = 0
        tot_ri_l = tot_ri_p = tot_ri_t = 0
        tot_gj_l = tot_gj_p = tot_gj_t = 0
        tot_grand = 0

        for r in query_data:
            # Sesuai data di gambar: Rawat Jalan & Gangguan Jiwa diisi 0
            rj_l = 0
            rj_p = 0
            rj_t = 0
            
            gj_l = 0
            gj_p = 0
            gj_t = 0

            # Rawat Inap dihitung dari total kunjungan per bulan (Pasien Hidup + Mati)
            # Karena View baru menggunakan nama kolom `pasien_keluar` (atau `kunjungan`), kita breakdown manual dari data dasarnya:
            ri_l = int((r.pasien_hidup_l or 0) + (r.pasien_mati_kurang_48jam_l or 0) + (r.pasien_mati_lebih_48jam_l or 0))
            ri_p = int((r.pasien_hidup_p or 0) + (r.pasien_mati_kurang_48jam_p or 0) + (r.pasien_mati_lebih_48jam_p or 0))
            ri_t = ri_l + ri_p
            
            # Kunjungan Grand Total (Ujung Kanan) = RJ + RI + GJ
            grand_t = rj_t + ri_t + gj_t
            
            # Tambahkan ke akumulator total tahunan
            tot_ri_l += ri_l
            tot_ri_p += ri_p
            tot_ri_t += ri_t
            tot_grand += grand_t

            items.append({
                "bulan": r.bulan,
                "tahun": r.tahun,
                "rawat_jalan_l": rj_l,
                "rawat_jalan_p": rj_p,
                "rawat_jalan_total": rj_t,
                "rawat_inap_l": ri_l,
                "rawat_inap_p": ri_p,
                "rawat_inap_total": ri_t,
                "gangguan_jiwa_l": gj_l,
                "gangguan_jiwa_p": gj_p,
                "gangguan_jiwa_total": gj_t,
                "kunjungan_grand_total": grand_t
            })

        # Kemas baris TOTAL SELURUH RS paling bawah
        total = None
        if items:
            total = {
                "tahun": tahun,
                "rawat_jalan_l": tot_rj_l,
                "rawat_jalan_p": tot_rj_p,
                "rawat_jalan_total": tot_rj_t,
                "rawat_inap_l": tot_ri_l,
                "rawat_inap_p": tot_ri_p,
                "rawat_inap_total": tot_ri_t,
                "gangguan_jiwa_l": tot_gj_l,
                "gangguan_jiwa_p": tot_gj_p,
                "gangguan_jiwa_total": tot_gj_t,
                "kunjungan_grand_total": tot_grand
            }

        return {"data": items, "total": total}