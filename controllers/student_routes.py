from flask import (Blueprint, render_template, request,
                   redirect, url_for, flash, current_app)
from controllers.database import db
from controllers.models import User, Student, Company, PlacementDrive, Application, Notification
from controllers.auth import role_required, get_current_user
import os

student_bp = Blueprint('student', __name__, url_prefix='/student')


def add_notification(user_id, message):
    db.session.add(Notification(user_id=user_id, message=message))


def get_current_student():
    return Student.query.filter_by(user_id=get_current_user().id).first()


# ── DASHBOARD ─────────────────────────────────────────────────────────
@student_bp.route('/dashboard')
@role_required('student')
def dashboard():
    student         = get_current_student()
    approved_drives = (PlacementDrive.query.filter_by(status='approved')
                       .order_by(PlacementDrive.created_at.desc()).all())
    my_apps         = (Application.query.filter_by(student_id=student.id)
                       .order_by(Application.application_date.desc()).all())
    applied_drive_ids = {a.drive_id for a in my_apps}
    return render_template('student/dashboard.html',
        student=student, approved_drives=approved_drives,
        my_apps=my_apps, applied_drive_ids=applied_drive_ids)


# ── BROWSE DRIVES ─────────────────────────────────────────────────────
@student_bp.route('/drives')
@role_required('student')
def drives():
    student = get_current_student()
    search  = request.args.get('search', '').strip()
    query   = PlacementDrive.query.filter_by(status='approved')
    if search:
        query = query.filter(
            (PlacementDrive.job_title.ilike(f'%{search}%')) |
            (PlacementDrive.required_skills.ilike(f'%{search}%'))
        )
    all_drives = query.order_by(PlacementDrive.created_at.desc()).all()
    if search:
        company_ids = [c.id for c in Company.query.filter(
            Company.company_name.ilike(f'%{search}%')).all()]
        extra = PlacementDrive.query.filter(
            PlacementDrive.status == 'approved',
            PlacementDrive.company_id.in_(company_ids)).all()
        seen = {d.id for d in all_drives}
        for d in extra:
            if d.id not in seen:
                all_drives.append(d)
    applied_drive_ids = {a.drive_id for a in
                         Application.query.filter_by(student_id=student.id).all()}
    return render_template('student/drives.html',
        drives=all_drives, search=search,
        applied_drive_ids=applied_drive_ids, student=student)


# ── APPLY ─────────────────────────────────────────────────────────────
@student_bp.route('/drives/<int:drive_id>/apply', methods=['POST'])
@role_required('student')
def apply_drive(drive_id):
    student = get_current_student()
    drive   = PlacementDrive.query.get_or_404(drive_id)
    if drive.status != 'approved':
        flash('This drive is not available.', 'danger')
        return redirect(url_for('student.drives'))
    if Application.query.filter_by(student_id=student.id, drive_id=drive_id).first():
        flash('You have already applied for this drive.', 'warning')
        return redirect(url_for('student.drives'))
    db.session.add(Application(student_id=student.id, drive_id=drive_id, status='Applied'))
    add_notification(drive.company.user_id,
        f'New application from {student.full_name} for "{drive.job_title}"')
    db.session.commit()
    flash(f'Successfully applied for "{drive.job_title}"!', 'success')
    return redirect(url_for('student.drives'))


# ── MY APPLICATIONS ───────────────────────────────────────────────────
@student_bp.route('/applications')
@role_required('student')
def applications():
    student = get_current_student()
    apps    = (Application.query.filter_by(student_id=student.id)
               .order_by(Application.application_date.desc()).all())
    return render_template('student/applications.html', applications=apps, student=student)


# ── DRIVE DETAIL ──────────────────────────────────────────────────────
@student_bp.route('/drives/<int:drive_id>')
@role_required('student')
def view_drive(drive_id):
    student = get_current_student()
    drive   = PlacementDrive.query.filter_by(id=drive_id, status='approved').first_or_404()
    already_applied = Application.query.filter_by(
        student_id=student.id, drive_id=drive_id).first()
    return render_template('student/view_drive.html',
        drive=drive, already_applied=already_applied, student=student)


# ── PROFILE ───────────────────────────────────────────────────────────
@student_bp.route('/profile', methods=['GET', 'POST'])
@role_required('student')
def profile():
    student = get_current_student()
    if request.method == 'POST':
        student.full_name = request.form.get('full_name', '').strip()
        student.phone     = request.form.get('phone', '').strip()
        student.degree    = request.form.get('degree', '').strip()
        student.branch    = request.form.get('branch', '').strip()
        cgpa_str = request.form.get('cgpa', '').strip()
        student.cgpa  = float(cgpa_str) if cgpa_str else None
        student.skills = request.form.get('skills', '').strip()
        resume_file = request.files.get('resume')
        if resume_file and resume_file.filename:
            import re
            allowed = {'pdf', 'doc', 'docx'}
            ext = resume_file.filename.rsplit('.', 1)[-1].lower()
            if ext in allowed:
                safe_user  = re.sub(r'[^\w\-]', '_', get_current_user().username)
                filename   = safe_user + '_resume.' + ext
                upload_dir = current_app.config['UPLOAD_FOLDER']
                os.makedirs(upload_dir, exist_ok=True)
                resume_file.save(os.path.join(upload_dir, filename))
                student.resume_path = filename
            else:
                flash('Invalid file type. Only PDF, DOC, DOCX allowed.', 'danger')
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('student.profile'))
    return render_template('student/profile.html', student=student)


# ── NOTIFICATIONS ─────────────────────────────────────────────────────
@student_bp.route('/notifications')
@role_required('student')
def notifications():
    user   = get_current_user()
    notifs = Notification.query.filter_by(user_id=user.id)\
                               .order_by(Notification.created_at.desc()).all()
    Notification.query.filter_by(user_id=user.id, is_read=False)\
                      .update({'is_read': True})
    db.session.commit()
    return render_template('student/notifications.html',
        notifications=notifs, student=get_current_student())
