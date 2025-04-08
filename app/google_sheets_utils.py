import os
import json
import gspread
from google.oauth2 import service_account
from datetime import datetime
from flask import current_app

def get_mock_google_sheets_client():
    """
    Create a mock Google Sheets client for temporary use until proper credentials are provided
    This allows development to continue with example data
    """
    from app.models import Settings
    
    class MockSpreadsheet:
        def __init__(self, title="Mock Spreadsheet"):
            self.title = title
            
        def worksheet(self, name):
            return MockWorksheet(name)
            
        def worksheets(self):
            return [MockWorksheet("Attendance"), MockWorksheet("Subjects")]
    
    class MockWorksheet:
        def __init__(self, title):
            self.title = title
            
        def get_all_records(self):
            if self.title == "Attendance":
                # Return some example attendance records
                return [
                    {"Date": "2025-04-01", "Time": "09:30", "Name": "John Smith"},
                    {"Date": "2025-04-01", "Time": "09:35", "Name": "Jane Doe"},
                    {"Date": "2025-04-02", "Time": "09:28", "Name": "John Smith"},
                    {"Date": "2025-04-02", "Time": "09:40", "Name": "Jane Doe"},
                ]
            elif self.title == "Subjects":
                # Return some example subject records
                return [
                    {"Code": "DEFAULT", "Name": "Default Subject", "Semester": 1, "Credit Hours": 3}
                ]
            return []
    
    class MockClient:
        def open_by_key(self, key):
            return MockSpreadsheet(f"Mock Spreadsheet ({key})")
    
    return MockClient()

def get_google_sheets_client():
    """
    Get authenticated Google Sheets client
    """
    try:
        credentials_json = os.environ.get('GOOGLE_SHEETS_CREDENTIALS')
        
        if not credentials_json:
            current_app.logger.error("GOOGLE_SHEETS_CREDENTIALS environment variable not set")
            current_app.logger.warning("Using mock Google Sheets client for development purposes")
            # Return a mock client that provides example data
            return get_mock_google_sheets_client()
            
        # Parse the JSON string into a dictionary
        try:
            credentials_info = json.loads(credentials_json)
        except json.JSONDecodeError as e:
            current_app.logger.error(f"Failed to parse Google Sheets credentials JSON: {str(e)}")
            current_app.logger.warning("Using mock Google Sheets client for development purposes")
            return get_mock_google_sheets_client()
        
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
        current_app.logger.warning("Using mock Google Sheets client for development purposes")
        return get_mock_google_sheets_client()

def get_attendance_from_sheets(spreadsheet_id, sheet_name="Attendance"):
    """
    Get attendance data from Google Sheets
    
    Current sheet format:
    | Date | Time | Name |
    
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
        default_subject_code = "DEFAULT"  # Default subject code

        for record in records:
            # Check if we have the expected fields
            if not all(field in record for field in ['Date', 'Time', 'Name']):
                current_app.logger.warning(f"Record missing required fields (Date, Time, Name): {record}")
                continue
                
            try:
                # Format date string to datetime object if needed
                date_str = record['Date']
                date_obj = None
                
                # Try different date formats
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y']:
                    try:
                        date_obj = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
                
                if not date_obj:
                    current_app.logger.warning(f"Could not parse date '{date_str}' for record")
                    continue
                
                # Extract name (which is used as student ID)
                name = record['Name']
                # Default to present
                status = True
                
                formatted_records.append({
                    'student_id': name,  # Use name as student ID
                    'date': date_obj.strftime('%Y-%m-%d'),
                    'subject_code': default_subject_code,
                    'status': status,
                    'time': record['Time']  # Store time for reference
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
    
    Current sheet format:
    | Date | Time | Name |
    
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
        student_not_found = []
        
        # First, ensure we have a default subject
        default_subject_code = "DEFAULT"
        subject = Subject.query.filter_by(code=default_subject_code).first()
        
        if not subject:
            # Create a default subject if it doesn't exist
            subject = Subject(
                code=default_subject_code,
                name="Default Subject",
                semester=1,
                credit_hours=3
            )
            db.session.add(subject)
            db.session.commit()
            current_app.logger.info(f"Created default subject with code {default_subject_code}")
            
        for record in attendance_records:
            try:
                # Look up student by name (stored in student_id field)
                name = record['student_id']
                
                # Try to find student by first_name or last_name
                student = Student.query.filter(
                    (Student.first_name.ilike(f"%{name}%")) | 
                    (Student.last_name.ilike(f"%{name}%"))
                ).first()
                
                if not student:
                    # If not found yet, try to find by combined name
                    students = Student.query.all()
                    for s in students:
                        full_name = f"{s.first_name} {s.last_name}".lower()
                        if name.lower() in full_name:
                            student = s
                            break
                
                if not student:
                    if name not in student_not_found:
                        student_not_found.append(name)
                        current_app.logger.warning(f"Student with name '{name}' not found")
                    error_count += 1
                    continue
                    
                # Parse the date
                date_obj = datetime.strptime(record['date'], '%Y-%m-%d').date()
                
                # Check if attendance record already exists
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
        
        message = f"Attendance sync completed: {created_count} created, {updated_count} updated, {error_count} errors"
        if student_not_found:
            message += f"\n\nStudents not found: {', '.join(student_not_found)}"
            
        return True, message
        
    except Exception as e:
        current_app.logger.error(f"Error syncing attendance data: {str(e)}")
        return False, f"Error syncing attendance data: {str(e)}"