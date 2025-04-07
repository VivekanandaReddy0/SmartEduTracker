from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Student, Mark, Attendance, Announcement, Subject
from app.dashboard.data_service import get_student_data
from app.utils import fetch_attendance_data, calculate_attendance_percentage, send_attendance_alert
from app.chatbot.assistant import get_ai_response
import json

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard', template_folder='templates')

@dashboard_bp.route('/')
@login_required
def index():
    if current_user.role == 'student':
        student = current_user.student
        
        # Fetch attendance data
        attendance_data, success = fetch_attendance_data(student.student_id)
        attendance_stats = {}
        
        if success:
            attendance_stats = calculate_attendance_percentage(attendance_data)
        
        # Get marks data
        marks = Mark.query.filter_by(student_id=student.id).all()
        
        # Get announcements
        announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(5).all()
        
        # Check if attendance alert needed
        if attendance_stats.get('overall', {}).get('low_attendance', False):
            flash('Your overall attendance is below 75%. Please attend classes regularly.', 'warning')
        
        return render_template(
            'dashboard.html',
            title='Dashboard',
            student=student,
            attendance_stats=attendance_stats,
            marks=marks,
            announcements=announcements
        )
    elif current_user.role == 'admin':
        # Admin dashboard
        students_count = Student.query.count()
        low_attendance_count = 0
        
        # Count students with low attendance (this would be better with a join or subquery)
        students = Student.query.all()
        for student in students:
            attendance_data, success = fetch_attendance_data(student.student_id)
            if success:
                attendance_stats = calculate_attendance_percentage(attendance_data)
                if attendance_stats.get('overall', {}).get('low_attendance', False):
                    low_attendance_count += 1
        
        announcements = Announcement.query.order_by(Announcement.created_at.desc()).limit(5).all()
        
        return render_template(
            'admin_dashboard.html',
            title='Admin Dashboard',
            students_count=students_count,
            low_attendance_count=low_attendance_count,
            announcements=announcements
        )
    else:
        flash('Unknown user role', 'danger')
        return redirect(url_for('index'))

@dashboard_bp.route('/profile')
@login_required
def profile():
    if current_user.role == 'student':
        student = current_user.student
        
        # Get marks data
        marks = Mark.query.filter_by(student_id=student.id).all()
        
        return render_template(
            'profile.html',
            title='Profile',
            student=student,
            marks=marks
        )
    else:
        flash('Only students can access profiles', 'warning')
        return redirect(url_for('dashboard.index'))

@dashboard_bp.route('/attendance')
@login_required
def attendance():
    if current_user.role == 'student':
        student = current_user.student
        
        # Fetch attendance data
        attendance_data, success = fetch_attendance_data(student.student_id)
        attendance_stats = {}
        
        if success:
            attendance_stats = calculate_attendance_percentage(attendance_data)
        
        return render_template(
            'attendance.html',
            title='Attendance',
            student=student,
            attendance_stats=attendance_stats,
            attendance_data=json.dumps(attendance_data) if success else '{}'
        )
    else:
        flash('Only students can access attendance', 'warning')
        return redirect(url_for('dashboard.index'))

@dashboard_bp.route('/marks')
@login_required
def marks():
    if current_user.role == 'student':
        student = current_user.student
        
        # Get marks data
        marks = Mark.query.filter_by(student_id=student.id).all()
        
        # Group by subject
        subject_marks = {}
        for mark in marks:
            subject = mark.subject.name
            if subject not in subject_marks:
                subject_marks[subject] = []
            subject_marks[subject].append(mark)
        
        return render_template(
            'marks.html',
            title='Marks & GPA',
            student=student,
            subject_marks=subject_marks,
            gpa=student.gpa
        )
    else:
        flash('Only students can access marks', 'warning')
        return redirect(url_for('dashboard.index'))

@dashboard_bp.route('/chat')
@login_required
def chat():
    return render_template('chat.html', title='AI Assistant')

@dashboard_bp.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    message = data.get('message')
    
    if not message:
        return jsonify({'error': 'No message provided'}), 400
    
    # Get chat history
    history = data.get('history', [])
    
    # Get AI response
    try:
        response = get_ai_response(message, history)
        
        return jsonify({
            'response': response
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Admin routes
@dashboard_bp.route('/admin/students')
@login_required
def admin_students():
    if current_user.role != 'admin':
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('dashboard.index'))
    
    students = Student.query.all()
    
    return render_template(
        'admin_students.html',
        title='Manage Students',
        students=students
    )

@dashboard_bp.route('/admin/announcements')
@login_required
def admin_announcements():
    if current_user.role != 'admin':
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('dashboard.index'))
    
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    
    return render_template(
        'admin_announcements.html',
        title='Manage Announcements',
        announcements=announcements
    )

@dashboard_bp.route('/admin/attendance')
@login_required
def admin_attendance():
    if current_user.role != 'admin':
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('dashboard.index'))
    
    students = Student.query.all()
    
    # Get list of students with low attendance
    low_attendance_students = []
    
    for student in students:
        attendance_data, success = fetch_attendance_data(student.student_id)
        if success:
            attendance_stats = calculate_attendance_percentage(attendance_data)
            if attendance_stats.get('overall', {}).get('low_attendance', False):
                low_attendance_students.append({
                    'student': student,
                    'attendance': attendance_stats['overall']['percentage']
                })
    
    return render_template(
        'admin_attendance.html',
        title='Attendance Management',
        students=students,
        low_attendance_students=low_attendance_students
    )

@dashboard_bp.route('/admin/send_alerts', methods=['POST'])
@login_required
def admin_send_alerts():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get student IDs from request
    data = request.get_json()
    student_ids = data.get('student_ids', [])
    
    if not student_ids:
        return jsonify({'error': 'No students selected'}), 400
    
    # Send alerts to selected students
    success_count = 0
    for student_id in student_ids:
        student = Student.query.get(student_id)
        if student:
            if send_attendance_alert(student):
                success_count += 1
    
    return jsonify({
        'success': True,
        'message': f'Sent alerts to {success_count} students'
    }), 200

@dashboard_bp.route('/admin/add_announcement', methods=['POST'])
@login_required
def admin_add_announcement():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    title = data.get('title')
    content = data.get('content')
    
    if not title or not content:
        return jsonify({'error': 'Title and content are required'}), 400
    
    # Create new announcement
    announcement = Announcement(
        title=title,
        content=content,
        created_by=current_user.admin.id
    )
    
    db.session.add(announcement)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Announcement added successfully'
    }), 201
