import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import current_app
from flask_mail import Message
from app import mail
from datetime import datetime, timedelta
import json

def get_google_sheet_client():
    """
    Authenticate and return a Google Sheets client
    """
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    
    # Check if credentials are in environment
    if os.environ.get('GOOGLE_CREDENTIALS'):
        # Use credentials from environment variable
        credentials_json = json.loads(os.environ.get('GOOGLE_CREDENTIALS'))
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_json, scope)
    else:
        # Try to use a local credentials file
        credentials = ServiceAccountCredentials.from_json_keyfile_name('google_credentials.json', scope)
    
    return gspread.authorize(credentials)

def fetch_attendance_data(student_id):
    """
    Fetch attendance data from Google Sheets for a specific student
    """
    try:
        client = get_google_sheet_client()
        sheet_id = current_app.config['GOOGLE_SHEET_ID']
        
        if not sheet_id:
            return {'error': 'Google Sheet ID not configured'}, False
        
        # Open the Google Sheet
        sheet = client.open_by_key(sheet_id)
        
        # Assuming the first worksheet contains attendance data
        attendance_sheet = sheet.get_worksheet(0)
        
        # Get all records from the sheet
        records = attendance_sheet.get_all_records()
        
        # Filter records for the specific student
        student_attendance = [record for record in records if record.get('student_id') == student_id]
        
        return student_attendance, True
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
    Calculate GPA from subject marks
    """
    if not marks:
        return 0.0
    
    grade_points = {
        'A': 4.0,
        'B': 3.0,
        'C': 2.0,
        'D': 1.0,
        'F': 0.0
    }
    
    total_points = 0
    total_credits = 0
    
    for mark in marks:
        subject = mark.subject
        grade = mark.grade
        credits = subject.credit_hours
        
        total_points += grade_points.get(grade, 0) * credits
        total_credits += credits
    
    return total_points / total_credits if total_credits > 0 else 0.0
