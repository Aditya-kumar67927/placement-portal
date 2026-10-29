from flask import (Blueprint, render_template, request,
                   redirect, url_for, flash, session)
from functools import wraps
from controllers.database import db
from controllers.models import User, Student, Company
import os

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# ── Session helpers ───────────────────────────────────────────────────
def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)
    return None


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            if session.get('user_role') not in roles:
                flash('Access denied.', 'danger')
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated
    return decorator


# ── LOGIN ─────────────────────────────────────────────────────────────
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect(url_for('auth.dashboard_redirect'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html')

        if not user.is_active:
            flash('Your account has been deactivated. Contact admin.', 'danger')
            return render_template('auth/login.html')

        if user.role == 'company':
            company = Company.query.filter_by(user_id=user.id).first()
            if company:
                if company.approval_status == 'pending':
                    flash('Your company registration is pending admin approval.', 'warning')
                    return render_template('auth/login.html')
                if company.approval_status == 'rejected':
                    flash('Your company registration was rejected.', 'danger')
                    return render_template('auth/login.html')
                if company.is_blacklisted:
                    flash('Your company has been blacklisted.', 'danger')
                    return render_template('auth/login.html')

        if user.role == 'student':
            student = Student.query.filter_by(user_id=user.id).first()
            if student and student.is_blacklisted:
                flash('Your account has been blacklisted.', 'danger')
                return render_template('auth/login.html')

        session['user_id']       = user.id
        session['user_role']     = user.role
        session['user_username'] = user.username

        flash(f'Welcome back, {user.username}!', 'success')
        return redirect(url_for('auth.dashboard_redirect'))

    return render_template('auth/login.html')


# ── REGISTER STUDENT ──────────────────────────────────────────────────
@auth_bp.route('/register/student', methods=['GET', 'POST'])
def register_student():
    if request.method == 'POST':
        username  = request.form.get('username', '').strip()
        email     = request.form.get('email', '').strip().lower()
        password  = request.form.get('password', '')
        confirm   = request.form.get('confirm_password', '')
        full_name = request.form.get('full_name', '').strip()
        phone     = request.form.get('phone', '').strip()
        degree    = request.form.get('degree', '').strip()
        branch    = request.form.get('branch', '').strip()
        cgpa      = request.form.get('cgpa', '').strip()
        skills    = request.form.get('skills', '').strip()

        if not all([username, email, password, full_name]):
            flash('Please fill all required fields.', 'danger')
            return render_template('auth/register_student.html', form=request.form)

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register_student.html', form=request.form)

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('auth/register_student.html', form=request.form)

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('auth/register_student.html', form=request.form)

        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return render_template('auth/register_student.html', form=request.form)

        resume_path = None
        resume_file = request.files.get('resume')
        if resume_file and resume_file.filename:
            from flask import current_app
            allowed = {'pdf', 'doc', 'docx'}
            ext = resume_file.filename.rsplit('.', 1)[-1].lower()
            if ext in allowed:
                safe_name  = f"{username}_resume.{ext}"
                upload_dir = current_app.config['UPLOAD_FOLDER']
                os.makedirs(upload_dir, exist_ok=True)
                resume_file.save(os.path.join(upload_dir, safe_name))
                resume_path = safe_name

        user = User(username=username, email=email, role='student')
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        student = Student(
            user_id     = user.id,
            full_name   = full_name,
            phone       = phone,
            degree      = degree,
            branch      = branch,
            cgpa        = float(cgpa) if cgpa else None,
            skills      = skills,
            resume_path = resume_path
        )
        db.session.add(student)
        db.session.commit()

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register_student.html', form={})


# ── REGISTER COMPANY ──────────────────────────────────────────────────
@auth_bp.route('/register/company', methods=['GET', 'POST'])
def register_company():
    if request.method == 'POST':
        username     = request.form.get('username', '').strip()
        email        = request.form.get('email', '').strip().lower()
        password     = request.form.get('password', '')
        confirm      = request.form.get('confirm_password', '')
        company_name = request.form.get('company_name', '').strip()
        industry     = request.form.get('industry', '').strip()
        website      = request.form.get('website', '').strip()
        hr_name      = request.form.get('hr_contact_name', '').strip()
        hr_email     = request.form.get('hr_contact_email', '').strip()
        hr_phone     = request.form.get('hr_contact_phone', '').strip()
        description  = request.form.get('description', '').strip()

        if not all([username, email, password, company_name]):
            flash('Please fill all required fields.', 'danger')
            return render_template('auth/register_company.html', form=request.form)

        if password != confirm:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register_company.html', form=request.form)

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('auth/register_company.html', form=request.form)

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('auth/register_company.html', form=request.form)

        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return render_template('auth/register_company.html', form=request.form)

        user = User(username=username, email=email, role='company')
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        company = Company(
            user_id          = user.id,
            company_name     = company_name,
            industry         = industry,
            website          = website,
            hr_contact_name  = hr_name,
            hr_contact_email = hr_email,
            hr_contact_phone = hr_phone,
            description      = description,
            approval_status  = 'pending'
        )
        db.session.add(company)
        db.session.commit()

        flash('Registration submitted! Please wait for admin approval.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/register_company.html', form={})


# ── LOGOUT ────────────────────────────────────────────────────────────
@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


# ── DASHBOARD REDIRECT ────────────────────────────────────────────────
@auth_bp.route('/dashboard')
def dashboard_redirect():
    role = session.get('user_role')
    if role == 'admin':
        return redirect(url_for('admin.dashboard'))
    elif role == 'company':
        return redirect(url_for('company.dashboard'))
    elif role == 'student':
        return redirect(url_for('student.dashboard'))
    return redirect(url_for('auth.login'))
