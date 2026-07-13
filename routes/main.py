"""Dashboard route'u."""

from flask import Blueprint, render_template

from models import Order, OrderStatus

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def dashboard():
    status_counts = {
        status: Order.query.filter_by(status=status).count()
        for status in OrderStatus.ALL
    }
    total_orders = Order.query.count()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    return render_template(
        'dashboard.html',
        status_counts=status_counts,
        total_orders=total_orders,
        recent_orders=recent_orders,
    )
