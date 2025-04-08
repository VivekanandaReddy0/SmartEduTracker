import os
from flask import current_app, flash, redirect, url_for
from flask_mail import Message
from app import mail
from datetime import datetime, timedelta
import json
from app.models import Attendance, Subject
from flask_login import current_user
from functools import wraps

# Configuration for Google Sheets - will be retrieved from database
USE_GOOGLE_SHEETS = True  # Default to True, actual usage depends on spreadsheet ID being set

def admin_required(f):
    """
    Custom decorator to restrict access to admin users only
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You do not have permission to access this page. Admin access required.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    """
    Custom decorator to restrict access to student users only
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'student':
            flash('You do not have permission to access this page. Student access required.', 'warning')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function

def fetch_attendance_from_google_sheets(student_id):
    """
    Fetch attendance data from Google Sheets for a specific student
    
    Args:
        student_id (str): The student ID
        
    Returns:
        tuple: (attendance_data, success)
    """
    try:
        from app.google_sheets_utils import get_attendance_from_sheets
        from app.models import Settings
        
        # Get spreadsheet ID from settings
        spreadsheet_id = Settings.get('ATTENDANCE_SPREADSHEET_ID', '')
        
        if not spreadsheet_id:
            current_app.logger.error("ATTENDANCE_SPREADSHEET_ID not set in database settings")
            return {'error': 'Google Sheets spreadsheet ID not configured'}, False
            
        # Get all attendance records from the sheet
        all_records = get_attendance_from_sheets(spreadsheet_id)
        
        if all_records is None:
            return {'error': 'Failed to get data from Google Sheets'}, False
            
        if not all_records:
            return [], True
            
        # Filter records for the specific student
        student_records = [
            {
                'date': record['date'],
                'subject_code': record['subject_code'],
                'subject': record['subject_code'],  # Placeholder, will be updated if subject info available
                'status': 'Present' if record['status'] else 'Absent'
            }
            for record in all_records if record['student_id'] == student_id
        ]
        
        # Try to get subject names from database
        try:
            from app.models import Subject
            
            for record in student_records:
                subject = Subject.query.filter_by(code=record['subject_code']).first()
                if subject:
                    record['subject'] = subject.name
        except Exception as e:
            current_app.logger.warning(f"Could not get subject names from database: {str(e)}")
            
        return student_records, True
        
    except Exception as e:
        current_app.logger.error(f"Error fetching attendance from Google Sheets: {str(e)}")
        return {'error': str(e)}, False

def fetch_attendance_data(student_id, use_google_sheets=None):
    """
    Fetch attendance data from database or Google Sheets for a specific student
    
    Args:
        student_id (str): The student ID
        use_google_sheets (bool, optional): Whether to use Google Sheets. 
                                         If None, falls back to USE_GOOGLE_SHEETS config
                                         
    Returns:
        tuple: (attendance_data, success)
    """
    try:
        from app.models import Student, Attendance, Subject, Settings
        
        # Get the student object from student_id string
        student = Student.query.filter_by(student_id=student_id).first()
        
        if not student:
            return {'error': 'Student not found'}, False
        
        # Get spreadsheet ID from settings
        spreadsheet_id = Settings.get('ATTENDANCE_SPREADSHEET_ID', '')
        
        # Determine if we should use Google Sheets
        use_sheets = USE_GOOGLE_SHEETS if use_google_sheets is None else use_google_sheets
        
        if use_sheets and spreadsheet_id:
            return fetch_attendance_from_google_sheets(student_id)
        
        # Fall back to database
        # Get attendance records for the student
        attendance_records = Attendance.query.filter_by(student_id=student.id).all()
        
        if not attendance_records:
            return [], True
        
        formatted_records = []
        
        for record in attendance_records:
            subject = Subject.query.get(record.subject_id)
            
            formatted_records.append({
                'date': record.date.strftime('%Y-%m-%d'),
                'subject': subject.name,
                'subject_code': subject.code,
                'status': 'Present' if record.status else 'Absent'
            })
        
        return formatted_records, True
    except Exception as e:
        current_app.logger.error(f"Error fetching attendance data: {str(e)}")
        return {'error': str(e)}, False

def calculate_attendance_percentage(attendance_data):
    """
    Calculate attendance percentage from attendance data
    """
    if not attendance_data or isinstance(attendance_data, dict) and 'error' in attendance_data:
        return {}
    
    subject_attendance = {}
    
    for record in attendance_data:
        subject = record.get('subject')
        status = record.get('status', '').lower() == 'present'
        
        if subject not in subject_attendance:
            subject_attendance[subject] = {'present': 0, 'total': 0}
        
        subject_attendance[subject]['total'] += 1
        if status:
            subject_attendance[subject]['present'] += 1
    
    # Calculate percentage for each subject
    for subject, data in subject_attendance.items():
        present = data['present']
        total = data['total']
        data['percentage'] = (present / total * 100) if total > 0 else 0
        data['low_attendance'] = data['percentage'] < 75
    
    # Calculate overall attendance
    total_present = sum(data['present'] for data in subject_attendance.values())
    total_classes = sum(data['total'] for data in subject_attendance.values())
    
    overall_percentage = (total_present / total_classes * 100) if total_classes > 0 else 0
    low_overall = overall_percentage < 75
    
    return {
        'subjects': subject_attendance,
        'overall': {
            'present': total_present,
            'total': total_classes,
            'percentage': overall_percentage,
            'low_attendance': low_overall
        }
    }

def send_attendance_alert(student):
    """
    Send an email alert for low attendance
    """
    try:
        attendance_data, success = fetch_attendance_data(student.student_id)
        
        if not success:
            return False
        
        attendance_stats = calculate_attendance_percentage(attendance_data)
        
        # Check if overall attendance is low
        if attendance_stats.get('overall', {}).get('low_attendance', False):
            msg = Message(
                subject='Low Attendance Alert',
                recipients=[student.user.email],
                body=f"""
Dear {student.first_name} {student.last_name},

This is to inform you that your overall attendance is below 75%, which is {attendance_stats['overall']['percentage']:.2f}%.

Please make sure to attend your classes regularly to meet the minimum attendance requirement.

Regards,
SmartEdu Admin
                """
            )
            mail.send(msg)
            return True
        
        # Check if any subject has low attendance
        low_subjects = [
            subject for subject, data in attendance_stats.get('subjects', {}).items()
            if data.get('low_attendance', False)
        ]
        
        if low_subjects:
            subject_list = '\n'.join([f"- {subject}: {attendance_stats['subjects'][subject]['percentage']:.2f}%" for subject in low_subjects])
            
            msg = Message(
                subject='Low Subject Attendance Alert',
                recipients=[student.user.email],
                body=f"""
Dear {student.first_name} {student.last_name},

This is to inform you that your attendance is below 75% in the following subjects:

{subject_list}

Please make sure to attend your classes regularly to meet the minimum attendance requirement.

Regards,
SmartEdu Admin
                """
            )
            mail.send(msg)
            return True
            
        return False
    except Exception as e:
        current_app.logger.error(f"Error sending attendance alert: {str(e)}")
        return False

def get_attendance_by_date(attendance_data, days=30):
    """
    Group attendance data by date for the charts
    """
    if not attendance_data or isinstance(attendance_data, dict) and 'error' in attendance_data:
        return {}
    
    today = datetime.now().date()
    start_date = today - timedelta(days=days)
    
    date_data = {}
    for i in range(days):
        current_date = start_date + timedelta(days=i)
        date_str = current_date.strftime('%Y-%m-%d')
        date_data[date_str] = {'present': 0, 'absent': 0}
    
    for record in attendance_data:
        record_date = datetime.strptime(record.get('date'), '%Y-%m-%d').date()
        date_str = record_date.strftime('%Y-%m-%d')
        
        if record_date >= start_date and record_date <= today and date_str in date_data:
            status = record.get('status', '').lower() == 'present'
            if status:
                date_data[date_str]['present'] += 1
            else:
                date_data[date_str]['absent'] += 1
    
    return date_data

def calculate_gpa(marks):
    """
    Calculate GPA from subject marks on a 10-point scale.
    Returns None if a student fails any subject (grade 'F').
    """
    if not marks:
        return 0.0
    
    grade_points = {
        'A': 10.0,
        'B': 8.0,
        'C': 6.0,
        'D': 4.0,
        'F': 0.0
    }
    
    # Check if student has failed any subject
    for mark in marks:
        if mark.grade == 'F':
            return None  # Return None if student failed any subject
    
    total_points = 0
    total_credits = 0
    
    for mark in marks:
        subject = mark.subject
        grade = mark.grade
        credits = subject.credit_hours
        
        total_points += grade_points.get(grade, 0) * credits
        total_credits += credits
    
    return total_points / total_credits if total_credits > 0 else 0.0

def update_student_gpa(student_id):
    """
    Recalculate and update the GPA for a student based on all their marks.
    
    Args:
        student_id (int): The student ID in the database
        
    Returns:
        float or None: The updated GPA value, or None if the student has failed any subject
    """
    from app.models import Student, Mark
    
    student = Student.query.get(student_id)
    if not student:
        return None
        
    student_marks = Mark.query.filter_by(student_id=student.id).all()
    gpa = calculate_gpa(student_marks)
    
    # Update the student's GPA
    student.gpa = gpa
    
    # Don't commit here, let the caller handle the transaction
    
    return gpa

def update_all_student_gpas():
    """
    Recalculate and update the GPA for all students in the database.
    This is useful to ensure all student GPAs are up-to-date.
    
    Returns:
        int: Number of students whose GPAs were updated
    """
    from app.models import Student, db
    
    students = Student.query.all()
    updated_count = 0
    
    for student in students:
        old_gpa = student.gpa
        new_gpa = update_student_gpa(student.id)
        
        if old_gpa != new_gpa:
            updated_count += 1
            
    # Commit all changes
    db.session.commit()
    
    return updated_count
