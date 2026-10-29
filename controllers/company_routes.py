from flask import Blueprint, render_template, request, redirect, url_for, flash
from controllers.database import db
from controllers.models import User, Student, Company, PlacementDrive, Application, Notification
from controllers.auth import role_required, get_current_user
from datetime import datetime

company_bp = Blueprint('company', __name__, url_prefix='/company')


def add_notification(user_id, message):
    db.session.add(Notification(user_id=user_id, message=message))


def get_current_company():
    return Company.query.filter_by(user_id=get_current_user().id).first()


# ── DASHBOARD ─────────────────────────────────────────────────────────
@company_bp.route('/dashboard')
@role_required('company')
def dashboard():
    company         = get_current_company()
    drives          = PlacementDrive.query.filter_by(company_id=company.id).all()
    total_drives    = len(drives)
    approved_drives = sum(1 for d in drives if d.status == 'approved')
    total_apps      = sum(len(d.applications) for d in drives)
    selected_count  = Application.query.join(PlacementDrive).filter(
                        PlacementDrive.company_id == company.id,
                        Application.status == 'Selected').count()
    recent_apps = (Application.query.join(PlacementDrive)
                   .filter(PlacementDrive.company_id == company.id)
                   .order_by(Application.application_date.desc())
                   .limit(5).all())
    return render_template('company/dashboard.html',
        company=company, drives=drives,
        total_drives=total_drives, approved_drives=approved_drives,
        total_apps=total_apps, selected_count=selected_count,
        recent_apps=recent_apps)


# ── DRIVES ────────────────────────────────────────────────────────────
@company_bp.route('/drives')
@role_required('company')
def drives():
    company    = get_current_company()
    all_drives = PlacementDrive.query.filter_by(company_id=company.id)\
                               .order_by(PlacementDrive.created_at.desc()).all()
    return render_template('company/drives.html', drives=all_drives, company=company)


@company_bp.route('/drives/new', methods=['GET', 'POST'])
@role_required('company')
def new_drive():
    company = get_current_company()
    if company.approval_status != 'approved':
        flash('Your company must be approved before posting drives.', 'warning')
        return redirect(url_for('company.dashboard'))

    if request.method == 'POST':
        job_title    = request.form.get('job_title', '').strip()
        job_desc     = request.form.get('job_description', '').strip()
        eligibility  = request.form.get('eligibility_criteria', '').strip()
        req_skills   = request.form.get('required_skills', '').strip()
        experience   = request.form.get('experience_required', '').strip()
        salary       = request.form.get('salary_range', '').strip()
        deadline_str = request.form.get('application_deadline', '').strip()

        if not job_title or not job_desc:
            flash('Job title and description are required.', 'danger')
            return render_template('company/new_drive.html', form=request.form, company=company)

        deadline = None
        if deadline_str:
            try:
                deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid deadline date.', 'danger')
                return render_template('company/new_drive.html', form=request.form, company=company)

        drive = PlacementDrive(
            company_id=company.id, job_title=job_title,
            job_description=job_desc, eligibility_criteria=eligibility,
            required_skills=req_skills, experience_required=experience,
            salary_range=salary, application_deadline=deadline, status='pending')
        db.session.add(drive)
        db.session.commit()
        flash('Placement drive submitted for admin approval.', 'info')
        return redirect(url_for('company.drives'))

    return render_template('company/new_drive.html', form={}, company=company)


@company_bp.route('/drives/<int:drive_id>/edit', methods=['GET', 'POST'])
@role_required('company')
def edit_drive(drive_id):
    company = get_current_company()
    drive   = PlacementDrive.query.filter_by(id=drive_id, company_id=company.id).first_or_404()

    if request.method == 'POST':
        drive.job_title            = request.form.get('job_title', '').strip()
        drive.job_description      = request.form.get('job_description', '').strip()
        drive.eligibility_criteria = request.form.get('eligibility_criteria', '').strip()
        drive.required_skills      = request.form.get('required_skills', '').strip()
        drive.experience_required  = request.form.get('experience_required', '').strip()
        drive.salary_range         = request.form.get('salary_range', '').strip()
        deadline_str = request.form.get('application_deadline', '').strip()
        if deadline_str:
            try:
                drive.application_deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid deadline date.', 'danger')
        drive.status = 'pending'
        db.session.commit()
        flash('Drive updated and re-submitted for approval.', 'info')
        return redirect(url_for('company.drives'))

    return render_template('company/edit_drive.html', drive=drive, company=company)


@company_bp.route('/drives/<int:drive_id>/close', methods=['POST'])
@role_required('company')
def close_drive(drive_id):
    company = get_current_company()
    drive   = PlacementDrive.query.filter_by(id=drive_id, company_id=company.id).first_or_404()
    drive.status = 'closed'
    db.session.commit()
    flash('Drive closed.', 'info')
    return redirect(url_for('company.drives'))


@company_bp.route('/drives/<int:drive_id>/delete', methods=['POST'])
@role_required('company')
def delete_drive(drive_id):
    company = get_current_company()
    drive   = PlacementDrive.query.filter_by(id=drive_id, company_id=company.id).first_or_404()
    db.session.delete(drive)
    db.session.commit()
    flash('Drive removed.', 'success')
    return redirect(url_for('company.drives'))


# ── APPLICATIONS ──────────────────────────────────────────────────────
@company_bp.route('/drives/<int:drive_id>/applications')
@role_required('company')
def drive_applications(drive_id):
    company = get_current_company()
    drive   = PlacementDrive.query.filter_by(id=drive_id, company_id=company.id).first_or_404()
    apps    = Application.query.filter_by(drive_id=drive.id).all()
    return render_template('company/applications.html', drive=drive, applications=apps, company=company)


@company_bp.route('/applications/<int:app_id>/update_status', methods=['POST'])
@role_required('company')
def update_app_status(app_id):
    company    = get_current_company()
    app        = Application.query.get_or_404(app_id)
    if app.drive.company_id != company.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('company.dashboard'))
    new_status = request.form.get('status')
    if new_status not in ['Applied', 'Shortlisted', 'Interview', 'Selected', 'Rejected']:
        flash('Invalid status.', 'danger')
        return redirect(url_for('company.drive_applications', drive_id=app.drive_id))
    app.status = new_status
    add_notification(app.student.user_id,
        f'Your application for "{app.drive.job_title}" at '
        f'{company.company_name} is now: {new_status}')
    db.session.commit()
    flash(f'Status updated to {new_status}.', 'success')
    return redirect(url_for('company.drive_applications', drive_id=app.drive_id))


@company_bp.route('/students/<int:student_id>/view')
@role_required('company')
def view_student_profile(student_id):
    student = Student.query.get_or_404(student_id)
    return render_template('company/view_student.html', student=student)


# ── PROFILE ───────────────────────────────────────────────────────────
@company_bp.route('/profile', methods=['GET', 'POST'])
@role_required('company')
def profile():
    company = get_current_company()
    if request.method == 'POST':
        company.company_name     = request.form.get('company_name', '').strip()
        company.industry         = request.form.get('industry', '').strip()
        company.website          = request.form.get('website', '').strip()
        company.hr_contact_name  = request.form.get('hr_contact_name', '').strip()
        company.hr_contact_email = request.form.get('hr_contact_email', '').strip()
        company.hr_contact_phone = request.form.get('hr_contact_phone', '').strip()
        company.description      = request.form.get('description', '').strip()
        db.session.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('company.profile'))
    return render_template('company/profile.html', company=company)


# ── NOTIFICATIONS ─────────────────────────────────────────────────────
@company_bp.route('/notifications')
@role_required('company')
def notifications():
    user   = get_current_user()
    notifs = Notification.query.filter_by(user_id=user.id)\
                               .order_by(Notification.created_at.desc()).all()
    Notification.query.filter_by(user_id=user.id, is_read=False)\
                      .update({'is_read': True})
    db.session.commit()
    return render_template('company/notifications.html', notifications=notifs)
