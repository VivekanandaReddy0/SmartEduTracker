import os
import json
import gspread
from google.oauth2 import service_account
from datetime import datetime
from flask import current_app

def get_google_sheets_client():
    """
    Get authenticated Google Sheets client
    """
    try:
        credentials_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
        
        if not credentials_json:
            current_app.logger.error("GOOGLE_SHEETS_CREDENTIALS environment variable not set")
            return None
            
        # Parse the JSON string into a dictionary
        credentials_info = json.loads(credentials_json)
        
        # Create credentials object
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        credentials = service_account.Credentials.from_service_account_info(credentials_info, scopes=scope)
        
        # Create and return the client
        client = gspread.authorize(credentials)
        return client
        
    except Exception as e:
        current_app.logger.error(f"Error getting Google Sheets client: {str(e)}")
        return None

def get_attendance_from_sheets(spreadsheet_id, sheet_name="Attendance"):
    """
    Get attendance data from Google Sheets
    
    Expected sheet format:
    | Student ID | Date | Subject Code | Status |
    
    Returns:
    List of dictionaries with attendance data or None in case of error
    """
    try:
        client = get_google_sheets_client()
        
        if not client:
            return None
            
        # Open the spreadsheet
        sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
        
        # Get all records
        records = sheet.get_all_records()
        
        if not records:
            current_app.logger.warning(f"No attendance records found in sheet '{sheet_name}'")
            return []
            
        # Format the records
        formatted_records = []
        for record in records:
            # Ensure required fields exist
            if not all(field in record for field in ['Student ID', 'Date', 'Subject Code', 'Status']):
                continue
                
            try:
                # Format date string to datetime object if needed
                date_str = record['Date']
                date_obj = None
                
                # Try different date formats
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                    try:
                        date_obj = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
                
                if not date_obj:
                    current_app.logger.warning(f"Could not parse date '{date_str}' for record")
                    continue
                    
                formatted_records.append({
                    'student_id': str(record['Student ID']),
                    'date': date_obj.strftime('%Y-%m-%d'),
                    'subject_code': record['Subject Code'],
                    'status': record['Status'].lower() == 'present'
                })
                
            except Exception as e:
                current_app.logger.warning(f"Error formatting record: {str(e)}")
                continue
                
        return formatted_records
        
    except Exception as e:
        current_app.logger.error(f"Error getting attendance from Google Sheets: {str(e)}")
        return None

def get_subject_from_sheets(spreadsheet_id, subject_code, sheet_name="Subjects"):
    """
    Get subject details from Google Sheets by subject code
    
    Expected sheet format:
    | Code | Name | Semester | Credit Hours |
    
    Returns:
    Dictionary with subject data or None if not found or in case of error
    """
    try:
        client = get_google_sheets_client()
        
        if not client:
            return None
            
        # Open the spreadsheet
        sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
        
        # Get all records
        records = sheet.get_all_records()
        
        if not records:
            current_app.logger.warning(f"No subject records found in sheet '{sheet_name}'")
            return None
            
        # Find the subject with matching code
        for record in records:
            if record.get('Code') == subject_code:
                return {
                    'code': record['Code'],
                    'name': record['Name'],
                    'semester': int(record['Semester']),
                    'credit_hours': int(record['Credit Hours'])
                }
                
        current_app.logger.warning(f"Subject with code '{subject_code}' not found")
        return None
        
    except Exception as e:
        current_app.logger.error(f"Error getting subject from Google Sheets: {str(e)}")
        return None

def sync_attendance_to_database(spreadsheet_id, sheet_name="Attendance"):
    """
    Sync attendance data from Google Sheets to the database
    
    Expected sheet format:
    | Student ID | Date | Subject Code | Status |
    
    Returns:
    Tuple (success, message)
    """
    from app import db
    from app.models import Student, Subject, Attendance
    
    try:
        # Get attendance data from sheets
        attendance_records = get_attendance_from_sheets(spreadsheet_id, sheet_name)
        
        if attendance_records is None:
            return False, "Failed to get attendance data from Google Sheets"
            
        if not attendance_records:
            return True, "No attendance records found in Google Sheets"
            
        updated_count = 0
        created_count = 0
        error_count = 0
        
        for record in attendance_records:
            try:
                # Get student by student_id
                student = Student.query.filter_by(student_id=record['student_id']).first()
                
                if not student:
                    current_app.logger.warning(f"Student with ID '{record['student_id']}' not found")
                    error_count += 1
                    continue
                    
                # Get subject by subject_code
                subject = Subject.query.filter_by(code=record['subject_code']).first()
                
                if not subject:
                    # Try to get subject from sheets
                    subject_data = get_subject_from_sheets(spreadsheet_id, record['subject_code'])
                    
                    if not subject_data:
                        current_app.logger.warning(f"Subject with code '{record['subject_code']}' not found")
                        error_count += 1
                        continue
                        
                    # Create the subject
                    subject = Subject(
                        code=subject_data['code'],
                        name=subject_data['name'],
                        semester=subject_data['semester'],
                        credit_hours=subject_data['credit_hours']
                    )
                    db.session.add(subject)
                    db.session.commit()
                    
                # Check if attendance record already exists
                date_obj = datetime.strptime(record['date'], '%Y-%m-%d').date()
                
                attendance = Attendance.query.filter_by(
                    student_id=student.id,
                    subject_id=subject.id,
                    date=date_obj
                ).first()
                
                if attendance:
                    # Update existing record
                    if attendance.status != record['status']:
                        attendance.status = record['status']
                        db.session.commit()
                        updated_count += 1
                else:
                    # Create new record
                    attendance = Attendance(
                        student_id=student.id,
                        subject_id=subject.id,
                        date=date_obj,
                        status=record['status']
                    )
                    db.session.add(attendance)
                    db.session.commit()
                    created_count += 1
                    
            except Exception as e:
                current_app.logger.error(f"Error processing attendance record: {str(e)}")
                error_count += 1
                continue
                
        return True, f"Attendance sync completed: {created_count} created, {updated_count} updated, {error_count} errors"
        
    except Exception as e:
        current_app.logger.error(f"Error syncing attendance data: {str(e)}")
        return False, f"Error syncing attendance data: {str(e)}"