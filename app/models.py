from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db, login_manager

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student' or 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    student = db.relationship('Student', backref='user', uselist=False, cascade='all, delete-orphan')
    admin = db.relationship('Admin', backref='user', uselist=False, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    program = db.Column(db.String(100), nullable=False)
    gpa = db.Column(db.Float, default=0.0)
    
    # Relationships
    attendances = db.relationship('Attendance', backref='student', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Student {self.first_name} {self.last_name}>'

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    
    def __repr__(self):
        return f'<Admin {self.first_name} {self.last_name}>'

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    semester = db.Column(db.Integer, nullable=False)
    credit_hours = db.Column(db.Integer, nullable=False)
    
    # Relationships
    attendances = db.relationship('Attendance', backref='subject', lazy=True)
    marks = db.relationship('Mark', backref='subject', lazy=True)
    
    def __repr__(self):
        return f'<Subject {self.code} - {self.name}>'

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.Boolean, default=False)  # True for present, False for absent
    
    def __repr__(self):
        return f'<Attendance {self.student_id} - {self.subject_id} - {self.date}>'

class Mark(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    quiz_marks = db.Column(db.Float, default=0.0)
    midterm_marks = db.Column(db.Float, default=0.0)
    final_marks = db.Column(db.Float, default=0.0)
    total_marks = db.Column(db.Float, default=0.0)
    grade = db.Column(db.String(2))
    
    # Relationship with Student
    student = db.relationship('Student', backref='marks')
    
    def calculate_total(self):
        self.total_marks = self.quiz_marks + self.midterm_marks + self.final_marks
        self.calculate_grade()
        
    def calculate_grade(self):
        # Modified grade calculation for 10-point scale (A=10, B=8, C=6, D=4, F=0)
        if self.total_marks >= 90:
            self.grade = 'A'  # 10 points
        elif self.total_marks >= 75:
            self.grade = 'B'  # 8 points
        elif self.total_marks >= 60:
            self.grade = 'C'  # 6 points
        elif self.total_marks >= 45:
            self.grade = 'D'  # 4 points
        else:
            self.grade = 'F'  # 0 points
            
    def __repr__(self):
        return f'<Mark {self.student_id} - {self.subject_id}>'

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=False)
    
    # Relationship
    admin = db.relationship('Admin', backref='announcements')
    
    def __repr__(self):
        return f'<Announcement {self.title}>'

class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='chat_history')
    
    def __repr__(self):
        return f'<ChatHistory {self.user_id} - {self.created_at}>'
