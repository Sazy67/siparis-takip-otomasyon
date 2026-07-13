"""SQLAlchemy veritabani modelleri: Order (Siparis) ve OrderItem (Siparis Kalemi)."""

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class OrderStatus:
    DRAFT = 'Taslak'
    IN_PRODUCTION = 'Uretimde'
    COMPLETED = 'Tamamlandi'
    SHIPPED = 'Sevk Edildi'
    SYNCED = 'Netsise Aktarildi'

    ALL = [DRAFT, IN_PRODUCTION, COMPLETED, SHIPPED, SYNCED]


class ItemStatus:
    PENDING = 'Bekliyor'
    PRODUCED = 'Uretildi'

    ALL = [PENDING, PRODUCED]


class ItemCategory:
    PROFILE = 'Profil'
    HARDWARE = 'Aksesuar'
    CONSUMABLE = 'Sarf'
    GASKET = 'Fitil'
    GLASS = 'Cam'

    ALL = [PROFILE, HARDWARE, CONSUMABLE, GASKET, GLASS]


class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    phone = db.Column(db.String(50))
    address = db.Column(db.String(500))
    tax_number = db.Column(db.String(50))  # Vergi No / TC

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                            onupdate=lambda: datetime.now(timezone.utc))

    orders = db.relationship('Order', backref='customer', lazy=True)

    def __repr__(self):
        return f'<Customer {self.name}>'


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    project_name = db.Column(db.String(200), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    responsible_person = db.Column(db.String(120))
    order_date = db.Column(db.Date)
    status = db.Column(db.String(30), nullable=False, default=OrderStatus.DRAFT)

    # Excel ozet/maliyet bilgileri (satir 52-58 civari)
    total_amount = db.Column(db.Float, default=0)
    # total_amount - kalemlerin duz toplami (Excel'deki iscilik/kar gibi kalem
    # disi farkin sabit kalmasi icin) - ilk yuklemede hesaplanip donmez.
    kalem_disi_fark = db.Column(db.Float, default=0)
    kdv_haric_malzeme_tutari = db.Column(db.Float)
    kdv_haric_atolye_teslim_tutari = db.Column(db.Float)
    kar_orani = db.Column(db.Float)
    aluminyum_kg = db.Column(db.Float)
    aluminyum_malzeme_tutari = db.Column(db.Float)
    aksesuar_tutari = db.Column(db.Float)
    sarf_tutari = db.Column(db.Float)
    fitil_tutari = db.Column(db.Float)
    iscilik_tutari = db.Column(db.Float)
    kdv_haric_camsiz_maliyet = db.Column(db.Float)

    # Vadeli fiyat: kullanici tarafindan girilen toplam ve hesaplanan fark orani
    vadeli_fiyat = db.Column(db.Float)
    vade_farki_orani = db.Column(db.Float)

    source_filename = db.Column(db.String(255))
    netsis_fatura_no = db.Column(db.String(50))
    netsis_synced_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                            onupdate=lambda: datetime.now(timezone.utc))

    items = db.relationship('OrderItem', backref='order', lazy=True,
                             cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Order {self.order_number} - {self.project_name}>'

    @property
    def item_count(self):
        return len(self.items)

    @property
    def produced_count(self):
        return sum(1 for i in self.items if i.status == ItemStatus.PRODUCED)

    @property
    def progress_percent(self):
        if not self.items:
            return 0
        return round((self.produced_count / len(self.items)) * 100, 1)


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)

    category = db.Column(db.String(30), nullable=False, default=ItemCategory.PROFILE)
    stock_code = db.Column(db.String(50))
    stock_name = db.Column(db.String(300))
    color = db.Column(db.String(50))

    quantity = db.Column(db.Float)              # Adet
    length = db.Column(db.String(20))            # Boy Uzunlugu (orn. "6,0" - metin olarak geldigi icin string)
    total_quantity = db.Column(db.Float)          # Gereken Miktar
    unit = db.Column(db.String(20))               # Birim (m, adet ...)

    # Cam kalemlerine ozel alanlar
    width_mm = db.Column(db.Float)
    height_mm = db.Column(db.Float)
    thickness_mm = db.Column(db.Float)
    area_m2 = db.Column(db.Float)

    unit_price = db.Column(db.Float)
    total_price = db.Column(db.Float)

    # Vadeli karsilik degerler (vade farki orani uygulandiginda doldurulur)
    vadeli_unit_price = db.Column(db.Float)
    vadeli_total_price = db.Column(db.Float)

    status = db.Column(db.String(20), nullable=False, default=ItemStatus.PENDING)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                            onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<OrderItem {self.stock_code} - {self.stock_name}>'
