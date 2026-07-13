"""Flask uygulama giris noktasi ve konfigurasyonu."""

import os

from flask import Flask

from models import db


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS = {'xlsx', 'xls'}


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    instance_path = os.environ.get('INSTANCE_PATH', app.instance_path)
    os.makedirs(instance_path, exist_ok=True)
    db_path = os.path.join(instance_path, 'siparis.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    upload_folder = os.environ.get('UPLOAD_FOLDER', os.path.join(app.root_path, 'uploads'))
    os.makedirs(upload_folder, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = upload_folder

    db.init_app(app)

    from routes.main import main_bp
    from routes.orders import orders_bp
    from routes.customers import customers_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(customers_bp)

    with app.app_context():
        db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
