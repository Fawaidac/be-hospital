# app/services/komplain_service.py
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, extract, func
from datetime import datetime, timedelta
from app.models.pde import PDEModel
from app.models.komplain import KomplainModel

class KomplainService:

    @staticmethod
    def get_all(
        db: Session,
        search: str = None,
        kategori: str = None,
        is_done: bool = None,
        recent: bool = None,
        nomor_act: str = None,
        page: int = 1,
        per_page: int = 10
    ):
        now = datetime.now()
        # Filter bulan berjalan & tahun berjalan
        query = db.query(KomplainModel).filter(
            extract('month', KomplainModel.tanggal) == now.month,
            extract('year', KomplainModel.tanggal) == now.year
        )

        if search:
            query = query.filter(
                or_(
                    KomplainModel.nama.like(f"%{search}%"),
                    KomplainModel.nama_pelapor.like(f"%{search}%"),
                    KomplainModel.ruangan.like(f"%{search}%"),
                    KomplainModel.permasalahan.like(f"%{search}%"),
                    KomplainModel.nomor_wa.like(f"%{search}%")
                )
            )

        if kategori == "simrs":
            keywords = ['simrs', 'rme', 'lemot', 'loading', 'konek', 'internet']
            query = query.filter(or_(*[KomplainModel.permasalahan.like(f"%{w}%") for w in keywords]))

        elif kategori == "maintanance":
            keywords = ['komputer', 'printer', 'tinta', 'mouse', 'booting', 'cpu']
            query = query.filter(or_(*[KomplainModel.permasalahan.like(f"%{w}%") for w in keywords]))

        if is_done is not None:
            if is_done:
                query = query.filter(KomplainModel.nomor_act.isnot(None))
            else:
                query = query.filter(KomplainModel.nomor_act.is_(None))
                if recent:
                    one_hour_ago = now - timedelta(hours=1)
                    query = query.filter(KomplainModel.tanggal >= one_hour_ago)

        if nomor_act is not None:
            if nomor_act == "null":
                query = query.filter(KomplainModel.nomor_act.is_(None))
            else:
                query = query.filter(KomplainModel.nomor_act == nomor_act)

        # Hitung Total Record Untuk Keperluan Validasi Pagination
        total = query.count()

        # Eksekusi Get Hasil Berdasarkan Aturan Halaman (Paginate & Order By Latest ID)
        offset = (page - 1) * per_page
        items = query.order_by(KomplainModel.id.desc()).offset(offset).limit(per_page).all()

        # Olah transform model array meniru properti $appends = ['status'] dan toArray() Laravel
        formatted_data = []
        for item in items:
            status_str = "DONE" if item.nomor_act is not None else "PENDING"
            
            pde_data = None
            if item.pde:
                pde_data = {"id": item.pde.id, "nama": item.pde.nama, "alamat": item.pde.alamat, "telp": item.pde.telp}
            elif item.nomor_act:
                # Fallback toArray() Laravel model logic
                pde_data = {"id": None, "nama": "PDE Team", "alamat": None, "telp": item.nomor_act}

            formatted_data.append({
                "id": item.id,
                "nama": item.nama,
                "nama_pelapor": item.nama_pelapor,
                "ruangan": item.ruangan,
                "permasalahan": item.permasalahan,
                "nomor_wa": item.nomor_wa,
                "nomor_act": item.nomor_act,
                "tanggal": item.tanggal,
                "status": status_str,
                "pde": pde_data
            })

        return {"current_page": page, "data": formatted_data, "total": total}

    @staticmethod
    def get_dashboard_count(db: Session):
        now = datetime.now()
        simrs_kws = ['simrs', 'rme', 'lemot', 'loading', 'konek', 'internet']
        maint_kws = ['komputer', 'printer', 'tinta', 'mouse', 'booting', 'cpu']

        # Query Dasar Bulan Berjalan
        base_filter = and_(
            extract('month', KomplainModel.tanggal) == now.month,
            extract('year', KomplainModel.tanggal) == now.year
        )

        ticket_open = db.query(KomplainModel).filter(base_filter, KomplainModel.nomor_act.is_(None)).count()
        ticket_done = db.query(KomplainModel).filter(base_filter, KomplainModel.nomor_act.isnot(None)).count()

        simrs_masuk = db.query(KomplainModel).filter(base_filter, or_(*[KomplainModel.permasalahan.like(f"%{w}%") for w in simrs_kws])).count()
        simrs_done = db.query(KomplainModel).filter(base_filter, KomplainModel.nomor_act.isnot(None), or_(*[KomplainModel.permasalahan.like(f"%{w}%") for w in simrs_kws])).count()

        maint_masuk = db.query(KomplainModel).filter(base_filter, or_(*[KomplainModel.permasalahan.like(f"%{w}%") for w in maint_kws])).count()
        maint_done = db.query(KomplainModel).filter(base_filter, KomplainModel.nomor_act.isnot(None), or_(*[KomplainModel.permasalahan.like(f"%{w}%") for w in maint_kws])).count()

        # Ambil Performa Tim PDE Terbanyak (Group By nomor_act)
        performance_raw = db.query(
            KomplainModel.nomor_act,
            func.count(KomplainModel.id).label('total')
        ).filter(base_filter, KomplainModel.nomor_act.isnot(None))\
            .group_by(KomplainModel.nomor_act)\
            .order_by(func.count(KomplainModel.id).desc()).all()

        pde_performance = []
        pde_team_counter = 1
        
        for row in performance_raw:
            # Cari relasi data_pde manual di session psc
            pde_rel = db.query(PDEModel).filter(PDEModel.telp == row.nomor_act).first()
            if pde_rel:
                pde_performance.append({
                    "id": pde_rel.id,
                    "nama": pde_rel.nama,
                    "alamat": pde_rel.alamat,
                    "telp": row.nomor_act,
                    "total": row.total
                })
            else:
                pde_performance.append({
                    "id": None,
                    "nama": f"Base PDE Team {pde_team_counter}",
                    "alamat": None,
                    "telp": row.nomor_act,
                    "total": row.total
                })
                pde_team_counter += 1

        return {
            "ticket_open": ticket_open,
            "ticket_done": ticket_done,
            "simrs_masuk": simrs_masuk,
            "simrs_done": simrs_done,
            "maintenance_masuk": maint_masuk,
            "maintenance_done": maint_done,
            "pde_performance": pde_performance
        }

    @staticmethod
    def get_data_team_pde(db: Session):
        distinct_acts = db.query(KomplainModel.nomor_act)\
            .filter(KomplainModel.nomor_act.isnot(None))\
            .distinct().order_by(KomplainModel.nomor_act).all()

        pde_teams = []
        pde_team_counter = 1

        for row in distinct_acts:
            pde_rel = db.query(PDEModel).filter(PDEModel.telp == row.nomor_act).first()
            if pde_rel:
                pde_teams.append({
                    "id": pde_rel.id,
                    "nama": pde_rel.nama,
                    "alamat": pde_rel.alamat,
                    "telp": row.nomor_act
                })
            else:
                pde_teams.append({
                    "id": None,
                    "nama": f"PDE Team {pde_team_counter}",
                    "alamat": None,
                    "telp": row.nomor_act
                })
                pde_team_counter += 1

        return pde_teams