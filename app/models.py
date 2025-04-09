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
    profile_photo = db.Column(db.LargeBinary, nullable=True)  # Optimized binary photo data
    photo_mimetype = db.Column(db.String(64), nullable=True)  # Store the image MIME type
    
    # Relationships
    attendances = db.relationship('Attendance', backref='student', lazy=True, cascade='all, delete-orphan')
    
    def set_profile_photo(self, photo_data, mimetype, max_size=(300, 300), quality=80):
        """
        Set optimized profile photo with reduced data usage
        
        Args:
            photo_data: The binary photo data
            mimetype: The MIME type of the image (e.g., 'image/jpeg', 'image/png')
            max_size: Maximum dimensions (width, height) to resize the image to
            quality: JPEG compression quality (0-100)
        """
        try:
            from PIL import Image
            import io
            
            # Create an image from binary data
            img = Image.open(io.BytesIO(photo_data))
            
            # Convert to RGB if PNG or other format with alpha channel
            if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
                img = background
            
            # Resize the image to reduce size while maintaining aspect ratio
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save to bytes with compression
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            
            # Store the optimized image
            self.profile_photo = output.getvalue()
            self.photo_mimetype = 'image/jpeg'  # Always save as JPEG for optimal compression
            
            return True
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False
    
    def get_profile_photo_url(self):
        """
        Get a data URL for the profile photo if it exists
        """
        if self.profile_photo and self.photo_mimetype:
            import base64
            encoded = base64.b64encode(self.profile_photo).decode('utf-8')
            return f"data:{self.photo_mimetype};base64,{encoded}"
        return None
    
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

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @classmethod
    def get(cls, key, default=None):
        """Get a setting value by key"""
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting else default
        
    @classmethod
    def set(cls, key, value):
        """Set a setting value by key"""
        setting = cls.query.filter_by(key=key).first()
        if setting:
            setting.value = value
        else:
            setting = cls(key=key, value=value)
            db.session.add(setting)
        db.session.commit()
        return setting
    
    def __repr__(self):
        return f'<Settings {self.key}>'
