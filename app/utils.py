import os
from flask import current_app
from flask_mail import Message
from app import mail
from datetime import datetime, timedelta
import json
from app.models import Attendance, Subject

def fetch_attendance_data(student_id):
    """
    Fetch attendance data from database for a specific student
    """
    try:
        from app.models import Student, Attendance, Subject
        
        # Get the student object from student_id string
        student = Student.query.filter_by(student_id=student_id).first()
        
        if not student:
            return {'error': 'Student not found'}, False
        
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
