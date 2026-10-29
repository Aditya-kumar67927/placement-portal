import os
from flask import Flask, redirect, url_for, session
from controllers.database import db
from controllers.config import Config


def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(Config)

    os.makedirs(os.path.join(app.root_path, 'instance'), exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    db.init_app(app)

    # ── Create tables and seed admin ──────────────────────────────────
    with app.app_context():
        from controllers.models import (User, Student, Company,
                                        PlacementDrive, Application, Notification)
        db.create_all()
        _seed_admin()

    # ── Blueprints ────────────────────────────────────────────────────
    from controllers.auth           import auth_bp
    from controllers.admin_routes   import admin_bp
    from controllers.company_routes import company_bp
    from controllers.student_routes import student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(company_bp)
    app.register_blueprint(student_bp)

    # ── Root redirect ─────────────────────────────────────────────────
    @app.route('/')
    def index():
        if session.get('user_id'):
            return redirect(url_for('auth.dashboard_redirect'))
        return redirect(url_for('auth.login'))

    # ── Context processor: inject session vars into all templates ─────
    @app.context_processor
    def inject_session():
        from controllers.models import Notification
        unread_count = 0
        user_id   = session.get('user_id')
        user_role = session.get('user_role')
        username  = session.get('user_username')
        if user_id:
            unread_count = Notification.query.filter_by(
                user_id=user_id, is_read=False).count()
        return dict(
            session_user_id   = user_id,
            session_user_role = user_role,
            session_username  = username,
            unread_count      = unread_count
        )

    # ── Context processor: today's date for deadline comparisons ──────
    @app.context_processor
    def inject_today():
        from datetime import date
        return dict(today=date.today())

    return app


def _seed_admin():
    from controllers.models import User
    if not User.query.filter_by(role='admin').first():
        admin = User(username='admin', email='admin@placehub.com', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print('Default admin created: admin@placehub.com / admin123')


app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
