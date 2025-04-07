import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import current_app
from app.models import Student, Subject, Mark

def get_student_data(student_id):
    """
    Get comprehensive student data including profile, attendance, and marks
    """
    # Fetch student details
    student = Student.query.filter_by(id=student_id).first()
    
    if not student:
        return {'error': 'Student not found'}, 404
    
    # Get attendance data from Google Sheets
    attendance_data = get_attendance_from_sheets(student.student_id)
    
    # Get marks data
    marks_data = get_student_marks(student_id)
    
    return {
        'profile': {
            'id': student.student_id,
            'name': f"{student.first_name} {student.last_name}",
            'semester': student.semester,
            'program': student.program,
            'gpa': student.gpa
        },
        'attendance': attendance_data,
        'marks': marks_data
    }, 200

def get_attendance_from_sheets(student_id):
    """
    Fetch attendance data from Google Sheets
    This is a helper function for get_student_data
    """
    try:
        # Set up Google Sheets credentials
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
        
        client = gspread.authorize(credentials)
        
        # Open the Google Sheet
        sheet_id = current_app.config['GOOGLE_SHEET_ID']
        if not sheet_id:
            return {'error': 'Google Sheet ID not configured'}
        
        sheet = client.open_by_key(sheet_id)
        
        # Assuming the first worksheet contains attendance data
        attendance_sheet = sheet.get_worksheet(0)
        
        # Get all records from the sheet
        records = attendance_sheet.get_all_records()
        
        # Filter records for the specific student
        student_attendance = [record for record in records if record.get('student_id') == student_id]
        
        return student_attendance
    except Exception as e:
        current_app.logger.error(f"Error fetching attendance data: {str(e)}")
        return {'error': str(e)}

def get_student_marks(student_id):
    """
    Get student marks for all subjects
    This is a helper function for get_student_data
    """
    marks = Mark.query.filter_by(student_id=student_id).all()
    
    if not marks:
        return []
    
    marks_data = []
    for mark in marks:
        subject = Subject.query.get(mark.subject_id)
        
        marks_data.append({
            'subject_code': subject.code,
            'subject_name': subject.name,
            'quiz_marks': mark.quiz_marks,
            'midterm_marks': mark.midterm_marks,
            'final_marks': mark.final_marks,
            'total_marks': mark.total_marks,
            'grade': mark.grade
        })
    
    return marks_data
