import os
import secrets

_BASE_DIR     = os.path.abspath(os.path.dirname(__file__))
_PROJECT_ROOT = os.path.dirname(_BASE_DIR)


class Config:
    SECRET_KEY                     = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    SQLALCHEMY_DATABASE_URI        = (
        'sqlite:///' + os.path.join(_PROJECT_ROOT, 'instance', 'placement_portal.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER                  = os.path.join(_PROJECT_ROOT, 'static', 'uploads', 'resumes')
    MAX_CONTENT_LENGTH             = 5 * 1024 * 1024
    ALLOWED_EXTENSIONS             = {'pdf', 'doc', 'docx'}
