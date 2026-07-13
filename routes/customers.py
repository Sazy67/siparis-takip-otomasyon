"""Cari (musteri) listesi, detayi ve siparislere cari baglama route'lari."""

import re

from flask import Blueprint, flash, redirect, render_template, request, url_for

from models import Customer, Order, db

customers_bp = Blueprint('customers', __name__)


def guess_customer_name(project_name):
    """'HASAN CAM 1056' -> 'HASAN CAM' (sondaki sayisal/kod kismini atar)."""
    cleaned = re.sub(r'\s+\S*\d\S*\s*$', '', project_name).strip()
    return cleaned or project_name.strip()


def get_or_create_customer(name):
    name = name.strip()
    if not name:
        return None

    # SQLite'in yerlesik lower() fonksiyonu Turkce karakterlerde (I/i/C/c vb.)
    # dogru kucultme yapmadigindan, eslestirme Python tarafinda yapilir.
    target = name.casefold()
    customer = next(
        (c for c in Customer.query.all() if c.name.casefold() == target),
        None,
    )
    if customer is None:
        customer = Customer(name=name)
        db.session.add(customer)
        db.session.flush()
    return customer


@customers_bp.route('/customers')
def list_customers():
    customers = Customer.query.order_by(Customer.name.asc()).all()
    return render_template('customers_list.html', customers=customers)


@customers_bp.route('/customer/<int:customer_id>')
def detail(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    orders = Order.query.filter_by(customer_id=customer.id).order_by(Order.created_at.desc()).all()
    return render_template('customer_detail.html', customer=customer, orders=orders)


@customers_bp.route('/customer/<int:customer_id>/update', methods=['POST'])
def update_customer(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    customer.phone = (request.form.get('phone') or '').strip() or None
    customer.address = (request.form.get('address') or '').strip() or None
    customer.tax_number = (request.form.get('tax_number') or '').strip() or None
    db.session.commit()
    flash('Cari bilgileri guncellendi.', 'success')
    return redirect(url_for('customers.detail', customer_id=customer.id))


@customers_bp.route('/order/<int:order_id>/set-customer', methods=['POST'])
def set_order_customer(order_id):
    order = Order.query.get_or_404(order_id)

    customer_id = request.form.get('customer_id')
    new_customer_name = (request.form.get('new_customer_name') or '').strip()

    if new_customer_name:
        customer = get_or_create_customer(new_customer_name)
        order.customer_id = customer.id if customer else None
    elif customer_id:
        customer = Customer.query.get_or_404(int(customer_id))
        order.customer_id = customer.id
    else:
        order.customer_id = None

    db.session.commit()
    flash('Siparisin cari baglantisi guncellendi.', 'success')
    return redirect(url_for('orders.detail', order_id=order.id))
