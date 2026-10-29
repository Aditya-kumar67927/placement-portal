from flask import Blueprint, render_template, request, redirect, url_for, flash
from controllers.database import db
from controllers.models import User, Student, Company, PlacementDrive, Application, Notification
from controllers.auth import role_required, get_current_user

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def add_notification(user_id, message):
    db.session.add(Notification(user_id=user_id, message=message))


# ── DASHBOARD ─────────────────────────────────────────────────────────
@admin_bp.route('/dashboard')
@role_required('admin')
def dashboard():
    total_students    = Student.query.count()
    total_companies   = Company.query.filter_by(approval_status='approved').count()
    total_drives      = PlacementDrive.query.filter_by(status='approved').count()
    total_apps        = Application.query.count()
    pending_companies = Company.query.filter_by(approval_status='pending').count()
    pending_drives    = PlacementDrive.query.filter_by(status='pending').count()
    placed_count      = Application.query.filter_by(status='Selected').count()
    recent_apps       = (Application.query
                         .order_by(Application.application_date.desc())
                         .limit(5).all())
    return render_template('admin/dashboard.html',
        total_students=total_students, total_companies=total_companies,
        total_drives=total_drives, total_apps=total_apps,
        pending_companies=pending_companies, pending_drives=pending_drives,
        placed_count=placed_count, recent_apps=recent_apps)


# ── COMPANIES ─────────────────────────────────────────────────────────
@admin_bp.route('/companies')
@role_required('admin')
def companies():
    search = request.args.get('search', '').strip()
    query  = Company.query
    if search:
        query = query.filter(
            (Company.company_name.ilike(f'%{search}%')) |
            (Company.industry.ilike(f'%{search}%'))
        )
    all_companies = query.order_by(Company.created_at.desc()).all()
    return render_template('admin/companies.html', companies=all_companies, search=search)


@admin_bp.route('/companies/<int:company_id>/approve', methods=['POST'])
@role_required('admin')
def approve_company(company_id):
    company = Company.query.get_or_404(company_id)
    company.approval_status = 'approved'
    add_notification(company.user_id,
        f'Your company "{company.company_name}" has been approved! You can now log in.')
    db.session.commit()
    flash(f'Company "{company.company_name}" approved.', 'success')
    return redirect(url_for('admin.companies'))


@admin_bp.route('/companies/<int:company_id>/reject', methods=['POST'])
@role_required('admin')
def reject_company(company_id):
    company = Company.query.get_or_404(company_id)
    company.approval_status = 'rejected'
    add_notification(company.user_id,
        f'Your company "{company.company_name}" registration was rejected.')
    db.session.commit()
    flash(f'Company "{company.company_name}" rejected.', 'warning')
    return redirect(url_for('admin.companies'))


@admin_bp.route('/companies/<int:company_id>/blacklist', methods=['POST'])
@role_required('admin')
def blacklist_company(company_id):
    company = Company.query.get_or_404(company_id)
    company.is_blacklisted = not company.is_blacklisted
    company.user.is_active = not company.is_blacklisted
    db.session.commit()
    state = 'blacklisted' if company.is_blacklisted else 'un-blacklisted'
    flash(f'Company "{company.company_name}" {state}.', 'info')
    return redirect(url_for('admin.companies'))


@admin_bp.route('/companies/<int:company_id>/delete', methods=['POST'])
@role_required('admin')
def delete_company(company_id):
    company = Company.query.get_or_404(company_id)
    user = company.user
    db.session.delete(company)
    db.session.delete(user)
    db.session.commit()
    flash('Company deleted.', 'success')
    return redirect(url_for('admin.companies'))


# ── STUDENTS ──────────────────────────────────────────────────────────
@admin_bp.route('/students')
@role_required('admin')
def students():
    search = request.args.get('search', '').strip()
    query  = Student.query.join(User)
    if search:
        query = query.filter(
            (Student.full_name.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%'))        |
            (Student.phone.ilike(f'%{search}%'))     |
            (User.username.ilike(f'%{search}%'))
        )
    all_students = query.order_by(Student.created_at.desc()).all()
    return render_template('admin/students.html', students=all_students, search=search)


@admin_bp.route('/students/<int:student_id>/blacklist', methods=['POST'])
@role_required('admin')
def blacklist_student(student_id):
    student = Student.query.get_or_404(student_id)
    student.is_blacklisted = not student.is_blacklisted
    student.user.is_active = not student.is_blacklisted
    db.session.commit()
    state = 'blacklisted' if student.is_blacklisted else 'un-blacklisted'
    flash(f'Student "{student.full_name}" {state}.', 'info')
    return redirect(url_for('admin.students'))


@admin_bp.route('/students/<int:student_id>/delete', methods=['POST'])
@role_required('admin')
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    user = student.user
    db.session.delete(student)
    db.session.delete(user)
    db.session.commit()
    flash('Student deleted.', 'success')
    return redirect(url_for('admin.students'))


@admin_bp.route('/students/<int:student_id>/view')
@role_required('admin')
def view_student(student_id):
    student = Student.query.get_or_404(student_id)
    apps = Application.query.filter_by(student_id=student.id)\
                            .order_by(Application.application_date.desc()).all()
    return render_template('admin/view_student.html', student=student, applications=apps)


# ── DRIVES ────────────────────────────────────────────────────────────
@admin_bp.route('/drives')
@role_required('admin')
def drives():
    status_filter = request.args.get('status', '')
    query = PlacementDrive.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    all_drives = query.order_by(PlacementDrive.created_at.desc()).all()
    return render_template('admin/drives.html', drives=all_drives, status_filter=status_filter)


@admin_bp.route('/drives/<int:drive_id>/approve', methods=['POST'])
@role_required('admin')
def approve_drive(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    drive.status = 'approved'
    add_notification(drive.company.user_id,
        f'Your placement drive "{drive.job_title}" has been approved!')
    for s in Student.query.join(User).filter(User.is_active == True,
                                              Student.is_blacklisted == False).all():
        add_notification(s.user_id,
            f'New drive: "{drive.job_title}" by {drive.company.company_name}')
    db.session.commit()
    flash(f'Drive "{drive.job_title}" approved.', 'success')
    return redirect(url_for('admin.drives'))


@admin_bp.route('/drives/<int:drive_id>/reject', methods=['POST'])
@role_required('admin')
def reject_drive(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    drive.status = 'rejected'
    add_notification(drive.company.user_id,
        f'Your drive "{drive.job_title}" was rejected by admin.')
    db.session.commit()
    flash(f'Drive "{drive.job_title}" rejected.', 'warning')
    return redirect(url_for('admin.drives'))


@admin_bp.route('/drives/<int:drive_id>/view')
@role_required('admin')
def view_drive(drive_id):
    drive = PlacementDrive.query.get_or_404(drive_id)
    apps  = Application.query.filter_by(drive_id=drive.id).all()
    return render_template('admin/view_drive.html', drive=drive, applications=apps)


# ── ALL APPLICATIONS ──────────────────────────────────────────────────
@admin_bp.route('/applications')
@role_required('admin')
def applications():
    all_apps = Application.query.order_by(Application.application_date.desc()).all()
    return render_template('admin/applications.html', applications=all_apps)


# ── NOTIFICATIONS ─────────────────────────────────────────────────────
@admin_bp.route('/notifications')
@role_required('admin')
def notifications():
    user   = get_current_user()
    notifs = Notification.query.filter_by(user_id=user.id)\
                               .order_by(Notification.created_at.desc()).all()
    Notification.query.filter_by(user_id=user.id, is_read=False)\
                      .update({'is_read': True})
    db.session.commit()
    return render_template('admin/notifications.html', notifications=notifs)
