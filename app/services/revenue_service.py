from sqlalchemy.orm import Session
from app.models.category_model import CategoryModel
from app.models.target_model import TargetModel
from app.models.revenue_model import RevenueModel
from app.models.revenue_detail import RevenueDetailModel
from fastapi import HTTPException, status

BULAN_MAP = {
    1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April', 5: 'Mei', 6: 'Juni',
    7: 'Juli', 8: 'Agustus', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
}

class RevenueService:
    
    @staticmethod
    def get_dashboard(db: Session, tahun: int):
        categories = db.query(CategoryModel).all()
        targets = db.query(TargetModel).filter(TargetModel.tahun == tahun).all()

        target_tahunan = {}
        target_bulanan = {}

        for cat in categories:
            t_tahunan = next((t for t in targets if t.category_id == cat.id and t.type == 'tahunan'), None)
            t_bulanan = next((t for t in targets if t.category_id == cat.id and t.type == 'bulanan'), None)
            
            target_tahunan[cat.name] = t_tahunan.amount if t_tahunan else 0
            target_bulanan[cat.name] = t_bulanan.amount if t_bulanan else 0

        jumlah_target_tahunan = sum(target_tahunan.values())
        jumlah_target_bulanan = sum(target_bulanan.values())

        revenues = db.query(RevenueModel).filter(RevenueModel.tahun == tahun).order_by(RevenueModel.bulan).all()

        realisasi_data = []
        summary_kategori = {cat.name: 0 for cat in categories}

        for bulan, bulan_name in BULAN_MAP.items():
            rev = next((r for r in revenues if r.bulan == bulan), None)
            
            data_kategori = []
            total_bulan = 0

            # Tarik detail ke memory jika revenue ada untuk optimasi looping
            details = db.query(RevenueDetailModel).filter(RevenueDetailModel.revenue_id == rev.id).all() if rev else []

            for cat in categories:
                detail = next((d for d in details if d.category_id == cat.id), None)
                amount = detail.amount if detail else 0
                target_bulan = target_bulanan.get(cat.name, 0)

                percentage = f"{(amount / target_bulan) * 100:.2f}" if target_bulan > 0 else "0.00"

                data_kategori.append({
                    'category': cat.name,
                    'amount': amount,
                    'percentage': percentage
                })

                total_bulan += amount
                summary_kategori[cat.name] += amount

            total_percentage = f"{(total_bulan / jumlah_target_bulanan) * 100:.2f}" if jumlah_target_bulanan > 0 else "0.00"

            realisasi_data.append({
                'bulan': bulan,
                'bulan_name': bulan_name,
                'categories': data_kategori,
                'total_bulan': total_bulan,
                'total_percentage': total_percentage
            })

        persentase_tahun = {}
        for cat in categories:
            target = target_tahunan.get(cat.name, 0)
            realisasi_cat = summary_kategori[cat.name]
            persentase_tahun[cat.name] = f"{(realisasi_cat / target) * 100:.2f}" if target > 0 else "0.00"

        grand_total_realisasi = sum(summary_kategori.values())
        grand_persentase_tahun = f"{(grand_total_realisasi / jumlah_target_tahunan) * 100:.2f}" if jumlah_target_tahunan > 0 else "0.00"

        return {
            'tahun': tahun,
            'target_tahunan': target_tahunan,
            'total_target_tahunan': jumlah_target_tahunan,
            'target_bulanan': target_bulanan,
            'total_target_bulanan': jumlah_target_bulanan,
            'realisasi': realisasi_data,
            'summary': {
                'total_per_kategori': summary_kategori,
                'persentase_tahun': persentase_tahun,
                'grand_total_realisasi': grand_total_realisasi,
                'grand_persentase_tahun': grand_persentase_tahun
            }
        }

    @staticmethod
    def store_or_update(db: Session, data: dict):
        tahun = data['tahun']
        categories = db.query(CategoryModel).all()

        # 1. Simpan/Update Target
        for target_input in data['targets']:
            category = next((c for c in categories if c.code == target_input['category_code']), None)
            if not category:
                raise HTTPException(status_code=400, detail=f"Kategori dengan code '{target_input['category_code']}' tidak ditemukan.")

            # Model Eloquent updateOrCreate dikonversi ke query + edit/add di SQLAlchemy
            for t_type, key_amount in [('tahunan', 'target_tahunan'), ('bulanan', 'target_bulanan')]:
                target_row = db.query(TargetModel).filter_by(tahun=tahun, category_id=category.id, type=t_type).first()
                if target_row:
                    target_row.amount = target_input.get(key_amount, 0)
                else:
                    new_target = TargetModel(tahun=tahun, category_id=category.id, type=t_type, amount=target_input.get(key_amount, 0))
                    db.add(new_target)

        db.flush() # Eksekusi id target sementara sebelum lanjut ke realisasi

        # 2. Simpan/Update Realisasi
        if 'realisasi' in data and data['realisasi']:
            for realisasi_bulan in data['realisasi']:
                bulan = realisasi_bulan['bulan']

                revenue = db.query(RevenueModel).filter_by(tahun=tahun, bulan=bulan).first()
                if not revenue:
                    revenue = RevenueModel(tahun=tahun, bulan=bulan)
                    db.add(revenue)
                    db.flush()

                for cat_input in realisasi_bulan['categories']:
                    category = next((c for c in categories if c.code == cat_input['category_code']), None)
                    if not category:
                        raise HTTPException(status_code=400, detail=f"Kategori dengan code '{cat_input['category_code']}' tidak ditemukan.")

                    target_bulanan_row = db.query(TargetModel).filter_by(tahun=tahun, category_id=category.id, type='bulanan').first()
                    target_bulanan_amount = target_bulanan_row.amount if target_bulanan_row else 0
                    amount_realisasi = cat_input.get('amount', 0)

                    percentage = (amount_realisasi / target_bulanan_amount) * 100 if target_bulanan_amount > 0 else 0.00

                    detail_row = db.query(RevenueDetailModel).filter_by(revenue_id=revenue.id, category_id=category.id).first()
                    if detail_row:
                        detail_row.amount = amount_realisasi
                        detail_row.percentage = round(percentage, 2)
                    else:
                        new_detail = RevenueDetailModel(
                            revenue_id=revenue.id, category_id=category.id,
                            amount=amount_realisasi, percentage=round(percentage, 2)
                        )
                        db.add(new_detail)
        
        db.commit()
        return RevenueService.get_by_year(db, tahun)

    @staticmethod
    def get_year_list(db: Session):
        target_years = db.query(TargetModel.tahun).distinct().all()
        revenue_years = db.query(RevenueModel.tahun).distinct().all()
        
        all_years = list(set([y[0] for y in target_years] + [y[0] for y in revenue_years]))
        all_years.sort()
        return all_years

    @staticmethod
    def get_by_year(db: Session, tahun: int):
        categories = db.query(CategoryModel).all()
        targets = db.query(TargetModel).filter(TargetModel.tahun == tahun).all()

        target_data = []
        for cat in categories:
            tahunan = next((t for t in targets if t.category_id == cat.id and t.type == 'tahunan'), None)
            bulanan = next((t for t in targets if t.category_id == cat.id and t.type == 'bulanan'), None)
            
            target_data.append({
                'category_code': cat.code,
                'category_name': cat.name,
                'target_tahunan': tahunan.amount if tahunan else 0,
                'target_bulanan': bulanan.amount if bulanan else 0,
            })

        revenues = db.query(RevenueModel).filter(RevenueModel.tahun == tahun).order_by(RevenueModel.bulan).all()
        realisasi_data = []
        
        for r in revenues:
            categories_data = []
            details = db.query(RevenueDetailModel).filter_by(revenue_id=r.id).all()
            
            for cat in categories:
                detail = next((d for d in details if d.category_id == cat.id), None)
                categories_data.append({
                    'category_code': cat.code,
                    'category_name': cat.name,
                    'amount': detail.amount if detail else 0
                })
                
            realisasi_data.append({
                'bulan': r.bulan,
                'bulan_name': BULAN_MAP.get(r.bulan, ''),
                'categories': categories_data
            })

        return {
            'tahun': tahun,
            'targets': target_data,
            'realisasi': realisasi_data
        }

    @staticmethod
    def delete_by_year(db: Session, tahun: int):
        try:
            revenues = db.query(RevenueModel).filter(RevenueModel.tahun == tahun).all()
            revenue_ids = [r.id for r in revenues]

            if revenue_ids:
                db.query(RevenueDetailModel).filter(RevenueDetailModel.revenue_id.in_(revenue_ids)).delete(synchronize_session=False)
                db.query(RevenueModel).filter(RevenueModel.id.in_(revenue_ids)).delete(synchronize_session=False)

            db.query(TargetModel).filter(TargetModel.tahun == tahun).delete(synchronize_session=False)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Gagal menghapus data: {str(e)}")