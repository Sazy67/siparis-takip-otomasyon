"""Siparis yukleme, listeleme, detay ve durum degistirme route'lari."""

import os
import uuid
from datetime import date, datetime

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from excel_parser import ExcelParseError, parse_order_excel
from models import Customer, ItemCategory, ItemStatus, Order, OrderItem, OrderStatus, db
from routes.customers import get_or_create_customer, guess_customer_name

orders_bp = Blueprint('orders', __name__)


def _allowed_file(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in current_app.config['ALLOWED_EXTENSIONS']


def _generate_order_number():
    today = date.today()
    prefix = f"SP-{today:%Y%m%d}-"
    count_today = Order.query.filter(Order.order_number.like(f'{prefix}%')).count()
    return f'{prefix}{count_today + 1:04d}'


@orders_bp.route('/order/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'GET':
        return render_template('upload.html')

    file = request.files.get('excel_file')
    if not file or file.filename == '':
        flash('Lutfen bir Excel dosyasi secin.', 'danger')
        return redirect(url_for('orders.upload'))

    if not _allowed_file(file.filename):
        flash('Sadece .xlsx veya .xls dosyalari yuklenebilir.', 'danger')
        return redirect(url_for('orders.upload'))

    original_filename = secure_filename(file.filename)
    saved_filename = f'{uuid.uuid4().hex[:8]}_{original_filename}'
    saved_path = os.path.join(current_app.config['UPLOAD_FOLDER'], saved_filename)
    file.save(saved_path)

    try:
        order_fields, order_items = parse_order_excel(saved_path)
    except ExcelParseError as exc:
        flash(f'Excel okunamadi: {exc}', 'danger')
        return redirect(url_for('orders.upload'))

    customer = get_or_create_customer(guess_customer_name(order_fields['project_name']))

    order = Order(
        order_number=_generate_order_number(),
        status=OrderStatus.DRAFT,
        source_filename=original_filename,
        customer_id=customer.id if customer else None,
        **order_fields,
    )
    db.session.add(order)
    db.session.flush()

    for item_fields in order_items:
        db.session.add(OrderItem(order_id=order.id, **item_fields))

    db.session.flush()
    kalem_toplami = sum(i.total_price or 0 for i in order.items)
    order.kalem_disi_fark = (order.total_amount or 0) - kalem_toplami

    db.session.commit()

    flash(f'Siparis basariyla olusturuldu: {order.order_number}', 'success')
    return redirect(url_for('orders.detail', order_id=order.id))


@orders_bp.route('/order/new', methods=['GET', 'POST'])
def new_order():
    if request.method == 'GET':
        all_customers = Customer.query.order_by(Customer.name.asc()).all()
        return render_template('order_new.html', all_customers=all_customers)

    project_name = request.form.get('project_name', '').strip()
    if not project_name:
        flash('Proje adi zorunludur.', 'danger')
        return redirect(url_for('orders.new_order'))

    order_date_raw = request.form.get('order_date', '').strip()
    order_date = None
    if order_date_raw:
        try:
            order_date = datetime.strptime(order_date_raw, '%Y-%m-%d').date()
        except ValueError:
            flash('Gecersiz tarih formati.', 'danger')
            return redirect(url_for('orders.new_order'))

    responsible_person = request.form.get('responsible_person', '').strip() or None

    customer_id = request.form.get('customer_id')
    new_customer_name = request.form.get('new_customer_name', '').strip()
    if new_customer_name:
        customer = get_or_create_customer(new_customer_name)
    elif customer_id:
        customer = Customer.query.get_or_404(int(customer_id))
    else:
        customer = None

    order = Order(
        order_number=_generate_order_number(),
        project_name=project_name,
        order_date=order_date,
        responsible_person=responsible_person,
        customer_id=customer.id if customer else None,
        status=OrderStatus.DRAFT,
        total_amount=0,
        kalem_disi_fark=0,
    )
    db.session.add(order)
    db.session.commit()

    flash(f'Siparis olusturuldu: {order.order_number}. Simdi kalem ekleyebilirsiniz.', 'success')
    return redirect(url_for('orders.detail', order_id=order.id))


@orders_bp.route('/orders')
def list_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('orders_list.html', orders=orders, statuses=OrderStatus.ALL)


@orders_bp.route('/order/<int:order_id>')
def detail(order_id):
    order = Order.query.get_or_404(order_id)
    items_by_category = {}
    for item in order.items:
        items_by_category.setdefault(item.category, []).append(item)
    all_customers = Customer.query.order_by(Customer.name.asc()).all()
    return render_template('order_detail.html', order=order, items_by_category=items_by_category,
                            all_customers=all_customers)


@orders_bp.route('/order/<int:order_id>/complete', methods=['POST'])
def complete(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = OrderStatus.COMPLETED
    db.session.commit()
    flash(f'{order.order_number} siparisi tamamlandi olarak isaretlendi.', 'success')
    return redirect(url_for('orders.detail', order_id=order.id))


@orders_bp.route('/order/<int:order_id>/ship', methods=['POST'])
def ship(order_id):
    order = Order.query.get_or_404(order_id)
    order.status = OrderStatus.SHIPPED
    db.session.commit()
    flash(f'{order.order_number} siparisi sevk edildi olarak isaretlendi.', 'success')
    return redirect(url_for('orders.detail', order_id=order.id))


@orders_bp.route('/order/<int:order_id>/item/<int:item_id>/toggle-status', methods=['POST'])
def toggle_item_status(order_id, item_id):
    item = OrderItem.query.filter_by(id=item_id, order_id=order_id).first_or_404()
    item.status = ItemStatus.PRODUCED if item.status == ItemStatus.PENDING else ItemStatus.PENDING
    db.session.commit()
    return jsonify({'id': item.id, 'status': item.status})


@orders_bp.route('/order/<int:order_id>/item/<int:item_id>/update', methods=['POST'])
def update_item(order_id, item_id):
    item = OrderItem.query.filter_by(id=item_id, order_id=order_id).first_or_404()
    order = item.order

    payload = request.get_json(silent=True) or {}
    raw_quantity = request.form.get('quantity', payload.get('quantity'))
    raw_unit_price = request.form.get('unit_price', payload.get('unit_price'))

    try:
        quantity = float(raw_quantity)
        unit_price = float(raw_unit_price)
    except (TypeError, ValueError):
        return jsonify({'error': 'Gecersiz adet veya fiyat degeri.'}), 400

    if quantity < 0 or unit_price < 0:
        return jsonify({'error': 'Adet ve fiyat negatif olamaz.'}), 400

    item.quantity = quantity
    item.unit_price = unit_price
    item.total_price = quantity * unit_price

    if order.vade_farki_orani is not None:
        item.vadeli_unit_price = item.unit_price * (1 + order.vade_farki_orani)
        item.vadeli_total_price = item.total_price * (1 + order.vade_farki_orani)

    order.total_amount = sum(i.total_price or 0 for i in order.items) + (order.kalem_disi_fark or 0)

    db.session.commit()

    return jsonify({
        'id': item.id,
        'quantity': item.quantity,
        'unit_price': item.unit_price,
        'total_price': item.total_price,
        'vadeli_unit_price': item.vadeli_unit_price,
        'vadeli_total_price': item.vadeli_total_price,
        'order_total_amount': order.total_amount,
    })


@orders_bp.route('/order/<int:order_id>/item/add', methods=['POST'])
def add_item(order_id):
    order = Order.query.get_or_404(order_id)

    category = request.form.get('category', '').strip()
    if category not in ItemCategory.ALL:
        flash('Gecerli bir kategori secin.', 'danger')
        return redirect(url_for('orders.detail', order_id=order.id))

    stock_name = request.form.get('stock_name', '').strip()
    if not stock_name:
        flash('Aciklama alani zorunludur.', 'danger')
        return redirect(url_for('orders.detail', order_id=order.id))

    try:
        quantity = float(request.form.get('quantity') or 0)
        unit_price = float(request.form.get('unit_price') or 0)
    except ValueError:
        flash('Adet ve fiyat sayisal olmalidir.', 'danger')
        return redirect(url_for('orders.detail', order_id=order.id))

    if quantity < 0 or unit_price < 0:
        flash('Adet ve fiyat negatif olamaz.', 'danger')
        return redirect(url_for('orders.detail', order_id=order.id))

    item = OrderItem(
        order_id=order.id,
        category=category,
        stock_code=(request.form.get('stock_code') or '').strip() or None,
        stock_name=stock_name,
        color=(request.form.get('color') or '').strip() or None,
        quantity=quantity,
        length=(request.form.get('length') or '').strip() or None,
        total_quantity=quantity,
        unit=(request.form.get('unit') or '').strip() or None,
        unit_price=unit_price,
        total_price=quantity * unit_price,
        status=ItemStatus.PENDING,
    )

    if order.vade_farki_orani is not None:
        item.vadeli_unit_price = item.unit_price * (1 + order.vade_farki_orani)
        item.vadeli_total_price = item.total_price * (1 + order.vade_farki_orani)

    db.session.add(item)
    db.session.flush()

    order.total_amount = sum(i.total_price or 0 for i in order.items) + (order.kalem_disi_fark or 0)

    db.session.commit()

    flash(f'"{item.stock_name}" siparise eklendi.', 'success')
    return redirect(url_for('orders.detail', order_id=order.id))


@orders_bp.route('/order/<int:order_id>/vadeli-fiyat', methods=['POST'])
def set_vadeli_fiyat(order_id):
    order = Order.query.get_or_404(order_id)

    try:
        vadeli_fiyat = float(request.form.get('vadeli_fiyat'))
    except (TypeError, ValueError):
        flash('Gecerli bir vadeli fiyat tutari girin.', 'danger')
        return redirect(url_for('orders.detail', order_id=order.id))

    if vadeli_fiyat <= 0:
        flash('Vadeli fiyat sifirdan buyuk olmalidir.', 'danger')
        return redirect(url_for('orders.detail', order_id=order.id))

    if not order.total_amount:
        flash('Nakit toplam tutar bulunamadigi icin vade farki hesaplanamadi.', 'danger')
        return redirect(url_for('orders.detail', order_id=order.id))

    oran = (vadeli_fiyat - order.total_amount) / order.total_amount

    order.vadeli_fiyat = vadeli_fiyat
    order.vade_farki_orani = oran

    for item in order.items:
        item.vadeli_unit_price = (item.unit_price or 0) * (1 + oran)
        item.vadeli_total_price = (item.total_price or 0) * (1 + oran)

    db.session.commit()

    flash(f'Vade farki (%{oran * 100:.2f}) tum kalemlere uygulandi.', 'success')
    return redirect(url_for('orders.detail', order_id=order.id))
