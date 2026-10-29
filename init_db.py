
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from controllers.database import db
from controllers.models import User


with app.app_context():
    db.create_all()
    print('All tables created.')

    if not User.query.filter_by(email='admin@placehub.com').first():
        admin = User(username='admin', email='admin@placehub.com', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

    print('\nLogin credentials:')
    print('  Admin   : admin@placehub.com  / admin123')

