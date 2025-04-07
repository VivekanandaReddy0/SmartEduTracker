from datetime import datetime, timedelta
from flask import current_app
from app.models import Student, Subject, Mark, Attendance

def get_student_data(student_id):
    """
    Get comprehensive student data including profile, attendance, and marks
    """
    # Fetch student details
    student = Student.query.filter_by(id=student_id).first()
    
    if not student:
        return {'error': 'Student not found'}, 404
    
    # Get attendance data from database
    attendance_data = get_attendance_from_database(student_id)
    
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

def get_attendance_from_database(student_id):
    """
    Fetch attendance data from database
    This is a helper function for get_student_data
    """
    try:
        # Get attendance records for the student
        attendance_records = Attendance.query.filter_by(student_id=student_id).all()
        
        if not attendance_records:
            return []
        
        attendance_data = []
        
        for record in attendance_records:
            subject = Subject.query.get(record.subject_id)
            
            attendance_data.append({
                'date': record.date.strftime('%Y-%m-%d'),
                'subject_code': subject.code,
                'subject_name': subject.name,
                'status': 'Present' if record.status else 'Absent'
            })
        
        return attendance_data
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
