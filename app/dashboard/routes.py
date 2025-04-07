from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Student, Mark, Attendance, Announcement, Subject
from app.dashboard.data_service import get_student_data
from app.utils import fetch_attendance_data, calculate_attendance_percentage, send_attendance_alert
from app.chatbot.assistant import get_ai_response
import json
import random

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
        attendance_records = []
        subject_names = []
        subject_percentages = []
        attendance_dates = []
        attendance_present = []
        attendance_absent = []
        overall_percentage = 0
        
        if success:
            attendance_stats = calculate_attendance_percentage(attendance_data)
            overall_percentage = attendance_stats.get('overall', {}).get('percentage', 0)
            
            # Format records for table display
            for record in attendance_data:
                attendance_records.append({
                    'date': record.get('date'),
                    'subject': record.get('subject_name', 'Unknown'),
                    'subject_code': record.get('subject_code', ''),
                    'status': record.get('status', False)
                })
            
            # Extract data for subject pie chart
            for subject, stats in attendance_stats.items():
                if subject != 'overall':
                    subject_names.append(subject)
                    subject_percentages.append(stats.get('percentage', 0))
            
            # Get attendance by date for history chart
            from app.utils import get_attendance_by_date
            date_attendance = get_attendance_by_date(attendance_data)
            for date, counts in date_attendance.items():
                attendance_dates.append(date)
                attendance_present.append(counts.get('present', 0))
                attendance_absent.append(counts.get('absent', 0))
        
        return render_template(
            'attendance.html',
            title='Attendance',
            student=student,
            attendance_stats=attendance_stats,
            attendance_records=attendance_records,
            overall_percentage=overall_percentage,
            subject_names=subject_names,
            subject_percentages=subject_percentages,
            attendance_dates=attendance_dates,
            attendance_present=attendance_present,
            attendance_absent=attendance_absent
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
        
        # Prepare data for the template
        marks_data = []
        subjects = []
        quiz_marks = []
        midterm_marks = []
        final_marks = []
        
        # For GPA chart
        semesters = list(range(1, student.semester + 1))
        semester_gpas = [round(3.0 + (random.random() * 0.8), 2) for _ in range(student.semester)]
        
        # Process marks data
        for mark in marks:
            subjects.append(mark.subject.name)
            quiz_marks.append(mark.quiz_marks)
            midterm_marks.append(mark.midterm_marks)
            final_marks.append(mark.final_marks)
            
            marks_data.append({
                'subject_name': mark.subject.name,
                'subject_code': mark.subject.code,
                'quiz_marks': mark.quiz_marks,
                'midterm_marks': mark.midterm_marks,
                'final_marks': mark.final_marks,
                'total_marks': mark.total_marks,
                'grade': mark.grade
            })
        
        return render_template(
            'marks.html',
            title='Marks & GPA',
            student=student,
            marks_data=marks_data,
            current_gpa=student.gpa,
            subjects=subjects,
            quiz_marks=quiz_marks,
            midterm_marks=midterm_marks,
            final_marks=final_marks,
            semesters=semesters,
            semester_gpas=semester_gpas
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

@dashboard_bp.route('/admin/sync_attendance', methods=['GET', 'POST'])
@login_required
def admin_sync_attendance():
    if current_user.role != 'admin':
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        from app.google_sheets_utils import sync_attendance_to_database
        import os
        
        spreadsheet_id = os.environ.get('ATTENDANCE_SPREADSHEET_ID', '')
        
        if not spreadsheet_id:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Spreadsheet ID not configured'}), 400
            flash('Google Sheets spreadsheet ID not configured', 'danger')
            return redirect(url_for('dashboard.admin_attendance'))
        
        success, message = sync_attendance_to_database(spreadsheet_id)
        
        if request.is_json:
            return jsonify({'success': success, 'message': message})
        
        if success:
            flash(message, 'success')
        else:
            flash(f'Error: {message}', 'danger')
            
        return redirect(url_for('dashboard.admin_attendance'))
    
    # GET request - show the sync page
    import os
    spreadsheet_id = os.environ.get('ATTENDANCE_SPREADSHEET_ID', '')
    
    return render_template(
        'admin_sync_attendance.html',
        title='Sync Attendance Data',
        spreadsheet_id=spreadsheet_id
    )

@dashboard_bp.route('/admin/set_spreadsheet_id', methods=['POST'])
@login_required
def admin_set_spreadsheet_id():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    spreadsheet_id = data.get('spreadsheet_id', '').strip()
    
    if not spreadsheet_id:
        return jsonify({'success': False, 'message': 'Spreadsheet ID is required'}), 400
    
    # In a real production application, we would store this in the database
    # or in environment variables that persist between app restarts
    # For this demo, we'll use an environment variable that lasts for the current session
    import os
    os.environ['ATTENDANCE_SPREADSHEET_ID'] = spreadsheet_id
    
    return jsonify({
        'success': True,
        'message': 'Spreadsheet ID set successfully'
    })

@dashboard_bp.route('/admin/test_sheets_connection', methods=['POST'])
@login_required
def admin_test_sheets_connection():
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    from app.google_sheets_utils import get_google_sheets_client
    import os
    
    try:
        # Get the Google Sheets client
        client = get_google_sheets_client()
        
        if not client:
            return jsonify({
                'success': False,
                'message': 'Failed to create Google Sheets client. Check your credentials.'
            }), 400
            
        # Get the spreadsheet ID
        spreadsheet_id = os.environ.get('ATTENDANCE_SPREADSHEET_ID', '')
        
        if not spreadsheet_id:
            return jsonify({
                'success': False,
                'message': 'Spreadsheet ID not configured'
            }), 400
            
        # Try to open the spreadsheet
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        # Get the list of worksheets
        worksheets = spreadsheet.worksheets()
        worksheet_names = [ws.title for ws in worksheets]
        
        # Check if required sheets exist
        has_attendance_sheet = 'Attendance' in worksheet_names
        has_subjects_sheet = 'Subjects' in worksheet_names
        
        return jsonify({
            'success': True,
            'message': 'Successfully connected to Google Sheets',
            'spreadsheet_title': spreadsheet.title,
            'worksheets': worksheet_names,
            'has_attendance_sheet': has_attendance_sheet,
            'has_subjects_sheet': has_subjects_sheet
        })
        
    except Exception as e:
        current_app.logger.error(f"Error testing Google Sheets connection: {str(e)}")
        
        return jsonify({
            'success': False,
            'message': f'Error connecting to Google Sheets: {str(e)}'
        }), 500

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
