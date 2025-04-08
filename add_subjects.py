from app import create_app, db
from app.models import Subject

app = create_app()

with app.app_context():
    # Check if any subjects already exist
    if Subject.query.count() == 0:
        # Create subjects
        subjects = [
            Subject(code="MTH101", name="Mathematics", semester=1, credit_hours=4),
            Subject(code="PHY101", name="Physics", semester=1, credit_hours=4),
            Subject(code="CHM101", name="Chemistry", semester=1, credit_hours=3),
            Subject(code="BEE101", name="Basic Electrical Engineering", semester=1, credit_hours=3),
            Subject(code="PPS101", name="Programming for Problem Solving", semester=1, credit_hours=4),
            Subject(code="ENG101", name="English", semester=1, credit_hours=2),
            Subject(code="DSC201", name="Data Structures in C++", semester=2, credit_hours=4),
        ]
        
        # Add subjects to the database
        for subject in subjects:
            db.session.add(subject)
        
        # Commit changes
        db.session.commit()
        
        print(f"Added {len(subjects)} subjects to the database")
    else:
        print("Subjects already exist in the database. No subjects were added.")
