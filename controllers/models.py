from controllers.database import db
from datetime import datetime
import hashlib
import os


class User(db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80),  unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role          = db.Column(db.String(20),  nullable=False)  # admin|company|student
    is_active     = db.Column(db.Boolean, default=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    student_profile = db.relationship('Student', back_populates='user',
                                      uselist=False, cascade='all, delete-orphan')
    company_profile = db.relationship('Company', back_populates='user',
                                      uselist=False, cascade='all, delete-orphan')

    def set_password(self, password):
        salt = os.urandom(16).hex()
        hashed = hashlib.sha256((salt + password).encode()).hexdigest()
        self.password_hash = f"{salt}${hashed}"

    def check_password(self, password):
        try:
            salt, hashed = self.password_hash.split('$', 1)
            return hashlib.sha256((salt + password).encode()).hexdigest() == hashed
        except Exception:
            return False

    def __repr__(self):
        return f'<User {self.username} [{self.role}]>'


class Student(db.Model):
    __tablename__ = 'students'

    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    full_name      = db.Column(db.String(120), nullable=False)
    phone          = db.Column(db.String(20))
    degree         = db.Column(db.String(120))
    branch         = db.Column(db.String(120))
    cgpa           = db.Column(db.Float)
    skills         = db.Column(db.Text)
    resume_path    = db.Column(db.String(255))
    is_blacklisted = db.Column(db.Boolean, default=False)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    user         = db.relationship('User',        back_populates='student_profile')
    applications = db.relationship('Application', back_populates='student',
                                   cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Student {self.full_name}>'


class Company(db.Model):
    __tablename__ = 'companies'

    id               = db.Column(db.Integer, primary_key=True)
    user_id          = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    company_name     = db.Column(db.String(150), nullable=False)
    industry         = db.Column(db.String(100))
    website          = db.Column(db.String(200))
    hr_contact_name  = db.Column(db.String(120))
    hr_contact_email = db.Column(db.String(120))
    hr_contact_phone = db.Column(db.String(20))
    description      = db.Column(db.Text)
    approval_status  = db.Column(db.String(20), default='pending')  # pending|approved|rejected
    is_blacklisted   = db.Column(db.Boolean, default=False)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    user             = db.relationship('User',           back_populates='company_profile')
    placement_drives = db.relationship('PlacementDrive', back_populates='company',
                                       cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Company {self.company_name}>'


class PlacementDrive(db.Model):
    __tablename__ = 'placement_drives'

    id                   = db.Column(db.Integer, primary_key=True)
    company_id           = db.Column(db.Integer, db.ForeignKey('companies.id'), nullable=False)
    job_title            = db.Column(db.String(150), nullable=False)
    job_description      = db.Column(db.Text,        nullable=False)
    eligibility_criteria = db.Column(db.Text)
    required_skills      = db.Column(db.Text)
    experience_required  = db.Column(db.String(50))
    salary_range         = db.Column(db.String(100))
    application_deadline = db.Column(db.Date)
    status               = db.Column(db.String(20), default='pending')  # pending|approved|closed|rejected
    created_at           = db.Column(db.DateTime, default=datetime.utcnow)

    company      = db.relationship('Company',     back_populates='placement_drives')
    applications = db.relationship('Application', back_populates='drive',
                                   cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Drive {self.job_title}>'


class Application(db.Model):
    __tablename__ = 'applications'

    id               = db.Column(db.Integer, primary_key=True)
    student_id       = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    drive_id         = db.Column(db.Integer, db.ForeignKey('placement_drives.id'), nullable=False)
    application_date = db.Column(db.DateTime, default=datetime.utcnow)
    status           = db.Column(db.String(30), default='Applied')
    # Applied | Shortlisted | Interview | Selected | Rejected

    student = db.relationship('Student',        back_populates='applications')
    drive   = db.relationship('PlacementDrive', back_populates='applications')

    __table_args__ = (
        db.UniqueConstraint('student_id', 'drive_id', name='uq_student_drive'),
    )

    def __repr__(self):
        return f'<Application student={self.student_id} drive={self.drive_id} [{self.status}]>'


class Notification(db.Model):
    __tablename__ = 'notifications'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message    = db.Column(db.Text, nullable=False)
    is_read    = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User')

    def __repr__(self):
        return f'<Notification user={self.user_id}>'
