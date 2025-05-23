from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Student, Mark, Attendance, Announcement, Subject, Settings
from app.dashboard.data_service import get_student_data
from app.utils import fetch_attendance_data, calculate_attendance_percentage, send_attendance_alert, admin_required, student_required
from app.chatbot.assistant import get_ai_response
from app.chatbot.grok_assistant import get_grok_response
import json
import random
from datetime import datetime, date

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
        
        # Check today's attendance status
        today = datetime.now().date()
        today_attendance = Attendance.query.filter_by(
            student_id=student.id,
            date=today
        ).all()
        
        # Determine if the student is present today in any class
        if today_attendance:
            is_present_today = any(a.status for a in today_attendance)
        else:
            is_present_today = False
        
        # Check if attendance alert needed
        if attendance_stats.get('overall', {}).get('low_attendance', False):
            flash('Your overall attendance is below 75%. Please attend classes regularly.', 'warning')
        
        return render_template(
            'dashboard.html',
            title='Dashboard',
            student=student,
            attendance_stats=attendance_stats,
            marks=marks,
            announcements=announcements,
            today=today,
            is_present_today=is_present_today
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

@dashboard_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@student_required
def profile():
    student = current_user.student
    
    if request.method == 'POST' and 'profile_photo' in request.files:
        # Handle photo upload
        photo_file = request.files['profile_photo']
        
        if photo_file and photo_file.filename:
            try:
                # Get the photo data and MIME type
                photo_data = photo_file.read()
                mimetype = photo_file.mimetype
                
                # Save the photo with optimization to reduce data usage
                if student.set_profile_photo(photo_data, mimetype):
                    db.session.commit()
                    flash('Profile photo updated successfully!', 'success')
                else:
                    flash('Error processing the uploaded image.', 'danger')
            except Exception as e:
                flash(f'Error uploading profile photo: {str(e)}', 'danger')
    
    # Get marks data
    marks = Mark.query.filter_by(student_id=student.id).all()
    
    return render_template(
        'profile.html',
        title='Profile',
        student=student,
        marks=marks
    )

@dashboard_bp.route('/attendance')
@login_required
@student_required
def attendance():
    student = current_user.student
    
    # Fetch attendance data from Google Sheets
    attendance_data, success = fetch_attendance_data(student.student_id, use_google_sheets=True)
    attendance_stats = {}
    attendance_records = []
    subject_names = []
    subject_percentages = []
    attendance_dates = []
    attendance_present = []
    attendance_absent = []
    overall_percentage = 0

    if not success:
        flash('Error fetching attendance data. Please try again later.', 'danger')
        return redirect(url_for('dashboard.index'))
    
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

@dashboard_bp.route('/marks')
@login_required
@student_required
def marks():
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
    
    # Prepare chart data
    gpa_chart_data = {
        'labels': semesters,
        'data': semester_gpas
    }
    
    marks_chart_data = {
        'subjects': subjects,
        'quiz': quiz_marks,
        'midterm': midterm_marks,
        'final': final_marks
    }
    
    # Format GPA for display
    current_gpa = 'F' if student.gpa is None else f"{student.gpa:.2f}"
    
    return render_template(
        'marks.html',
        title='Marks & GPA',
        student=student,
        marks=marks,
        current_gpa=current_gpa,
        gpa_chart_data=gpa_chart_data,
        marks_chart_data=marks_chart_data
    )

@dashboard_bp.route('/chat')
@login_required
@student_required
def chat():
    return render_template('chat.html', title='AI Assistant')

@dashboard_bp.route('/api/chat', methods=['POST'])
@login_required
@student_required
def api_chat():
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    message = data.get('message')
    
    if not message:
        return jsonify({'error': 'No message provided'}), 400
    
    # Get chat history
    history = data.get('history', [])
    
    # Check which AI model to use
    model = data.get('model', 'openai')  # Default to OpenAI if not specified
    
    # Get AI response based on selected model
    try:
        if model == 'grok':
            response = get_grok_response(message, history)
        else:
            response = get_ai_response(message, history)
        
        return jsonify({
            'response': response,
            'model': model
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Admin routes
@dashboard_bp.route('/admin/students')
@login_required
@admin_required
def admin_students():
    
    students = Student.query.all()
    
    return render_template(
        'admin_students.html',
        title='Manage Students',
        students=students
    )

@dashboard_bp.route('/admin/announcements')
@login_required
@admin_required
def admin_announcements():
    
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    
    return render_template(
        'admin_announcements.html',
        title='Manage Announcements',
        announcements=announcements
    )

@dashboard_bp.route('/admin/attendance')
@login_required
@admin_required
def admin_attendance():
    
    students = Student.query.all()
    subjects = Subject.query.all()  # Get all subjects
    
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
        subjects=subjects,
        low_attendance_students=low_attendance_students
    )

@dashboard_bp.route('/admin/sync_attendance', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_sync_attendance():
    
    if request.method == 'POST':
        from app.google_sheets_utils import sync_attendance_to_database
        from app.models import Settings
        
        spreadsheet_id = Settings.get('ATTENDANCE_SPREADSHEET_ID', '')
        
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
    from app.models import Settings
    spreadsheet_id = Settings.get('ATTENDANCE_SPREADSHEET_ID', '')
    
    return render_template(
        'admin_sync_attendance.html',
        title='Sync Attendance Data',
        spreadsheet_id=spreadsheet_id
    )

@dashboard_bp.route('/admin/set_spreadsheet_id', methods=['POST'])
@login_required
@admin_required
def admin_set_spreadsheet_id():
    
    data = request.get_json()
    spreadsheet_id = data.get('spreadsheet_id', '').strip()
    
    if not spreadsheet_id:
        return jsonify({'success': False, 'message': 'Spreadsheet ID is required'}), 400
    
    # Store the spreadsheet ID in the database
    from app.models import Settings
    Settings.set('ATTENDANCE_SPREADSHEET_ID', spreadsheet_id)
    
    return jsonify({
        'success': True,
        'message': 'Spreadsheet ID set successfully'
    })

@dashboard_bp.route('/admin/test_sheets_connection', methods=['POST'])
@login_required
@admin_required
def admin_test_sheets_connection():
    
    from app.google_sheets_utils import get_google_sheets_client
    from app.models import Settings
    import os
    import json
    
    try:
        # Debug the Google Sheets credentials
        credentials_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
        if not credentials_json:
            return jsonify({
                'success': False,
                'message': 'Google Sheets credentials not found in environment variables.'
            }), 400
        
        # Log the first few characters of the credentials (safely)
        creds_start = credentials_json[:20] + "..." if len(credentials_json) > 20 else credentials_json
        current_app.logger.info(f"Credentials start with: {creds_start}")
        
        # Try to parse the JSON
        try:
            creds_dict = json.loads(credentials_json)
            current_app.logger.info("Successfully parsed credentials JSON")
        except json.JSONDecodeError as e:
            return jsonify({
                'success': False,
                'message': f'Failed to parse Google Sheets credentials JSON: {str(e)}'
            }), 400
        
        # Get the Google Sheets client
        client = get_google_sheets_client()
        
        if not client:
            return jsonify({
                'success': False,
                'message': 'Failed to create Google Sheets client. Check your credentials.'
            }), 400
            
        # Get the spreadsheet ID from settings
        spreadsheet_id = Settings.get('ATTENDANCE_SPREADSHEET_ID', '')
        
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
        
        # Add additional debug information
        debug_info = {
            'error_type': type(e).__name__,
            'has_credentials': bool(os.environ.get('GOOGLE_SHEETS_CREDENTIALS')),
            'credentials_length': len(os.environ.get('GOOGLE_SHEETS_CREDENTIALS', '')) if os.environ.get('GOOGLE_SHEETS_CREDENTIALS') else 0,
            'spreadsheet_id': Settings.get('ATTENDANCE_SPREADSHEET_ID', ''),
        }
        
        return jsonify({
            'success': False,
            'message': f'Error connecting to Google Sheets: {str(e)}',
            'debugInfo': debug_info
        }), 500

@dashboard_bp.route('/admin/add_attendance', methods=['POST'])
@login_required
@admin_required
def admin_add_attendance():
    data = request.get_json()
    
    try:
        attendance = Attendance(
            student_id=data['student_id'],
            subject_id=data['subject_id'],
            date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            status=data['status']
        )
        db.session.add(attendance)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Attendance record added successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@dashboard_bp.route('/admin/send_alerts', methods=['POST'])
@login_required
@admin_required
def admin_send_alerts():
    
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

@dashboard_bp.route('/admin/marks', methods=['GET'])
@login_required
@admin_required
def admin_marks():
    
    students = Student.query.all()
    subjects = Subject.query.all()
    
    # Get all marks organized by student
    student_marks = {}
    for student in students:
        marks = Mark.query.filter_by(student_id=student.id).all()
        student_marks[student.id] = marks
    
    return render_template(
        'admin_marks.html',
        title='Manage Student Marks',
        students=students,
        subjects=subjects,
        student_marks=student_marks
    )

@dashboard_bp.route('/admin/recalculate_all_gpas', methods=['POST'])
@login_required
@admin_required
def admin_recalculate_all_gpas():
    """Recalculate GPA for all students"""
    from app.utils import update_all_student_gpas
    
    try:
        updated_count = update_all_student_gpas()
        return jsonify({
            'success': True,
            'message': f'Successfully updated GPA for {updated_count} students'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error updating GPAs: {str(e)}'
        }), 500

@dashboard_bp.route('/admin/edit_mark', methods=['POST'])
@login_required
@admin_required
def admin_edit_mark():
    
    data = request.get_json()
    mark_id = data.get('mark_id')
    student_id = data.get('student_id')
    subject_id = data.get('subject_id')
    quiz_marks = data.get('quiz_marks')
    midterm_marks = data.get('midterm_marks')
    final_marks = data.get('final_marks')
    
    # Validate inputs
    if not student_id or not subject_id:
        return jsonify({'success': False, 'message': 'Student and subject are required'}), 400
    
    try:
        quiz_marks = float(quiz_marks) if quiz_marks is not None else 0
        midterm_marks = float(midterm_marks) if midterm_marks is not None else 0
        final_marks = float(final_marks) if final_marks is not None else 0
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid mark values'}), 400
    
    if mark_id:
        # Update existing mark
        mark = Mark.query.get(mark_id)
        if not mark:
            return jsonify({'success': False, 'message': 'Mark not found'}), 404
            
        mark.quiz_marks = quiz_marks
        mark.midterm_marks = midterm_marks
        mark.final_marks = final_marks
        mark.calculate_total()
    else:
        # Create new mark
        mark = Mark(
            student_id=student_id,
            subject_id=subject_id,
            quiz_marks=quiz_marks,
            midterm_marks=midterm_marks,
            final_marks=final_marks
        )
        mark.calculate_total()
        db.session.add(mark)
    
    # Update student GPA
    from app.utils import update_student_gpa
    update_student_gpa(student_id)
    
    try:
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': 'Mark updated successfully',
            'total_marks': mark.total_marks,
            'grade': mark.grade
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@dashboard_bp.route('/admin/delete_mark/<int:mark_id>', methods=['POST'])
@login_required
@admin_required
def admin_delete_mark(mark_id):
    
    mark = Mark.query.get(mark_id)
    if not mark:
        return jsonify({'success': False, 'message': 'Mark not found'}), 404
    
    student_id = mark.student_id
    
    try:
        db.session.delete(mark)
        
        # Update student GPA
        from app.utils import update_student_gpa
        update_student_gpa(student_id)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Mark deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@dashboard_bp.route('/admin/add_announcement', methods=['POST'])
@login_required
@admin_required
def admin_add_announcement():
    
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
    
@dashboard_bp.route('/admin/today_attendance', methods=['GET'])
@login_required
@admin_required
def admin_today_attendance():
    """View for displaying today's attendance records"""
    
    # Get today's date
    today = datetime.now().date()
    
    # Get all students
    students = Student.query.all()
    
    # Get all attendance records for today
    today_attendance = {}
    for student in students:
        # Check if the student has an attendance record for today
        attendance = Attendance.query.filter_by(
            student_id=student.id,
            date=today
        ).all()
        
        # Store the attendance status (present/absent) for each student
        if attendance:
            # A student might have multiple attendance records for different subjects
            # Consider them present if they were present in at least one class
            present_in_any = any(a.status for a in attendance)
            today_attendance[student.id] = present_in_any
        else:
            today_attendance[student.id] = False  # Default to absent if no record exists
    
    return render_template(
        'admin_today_attendance.html',
        title="Today's Attendance",
        students=students,
        today_attendance=today_attendance,
        today=today
    )
