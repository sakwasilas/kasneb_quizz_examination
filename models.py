from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime, Boolean,Float
from sqlalchemy.orm import relationship
from datetime import datetime
from connection import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    role = Column(String(10), default='student')  # 'admin' or 'student'

   
    profile = relationship(
        'StudentProfile',
        uselist=False,
        back_populates='user',
        cascade='all, delete-orphan'
    )

    results = relationship('Result', backref='student')

class StudentProfile(Base):
    __tablename__ = 'student_profiles'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    full_name = Column(String(100))
    
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=False)  
    course = relationship('Course') 
    level = Column(String(50))
    kasneb_no = Column(String(50))
    profile_completed = Column(Boolean, default=False)

    user = relationship('User', back_populates='profile')

    

class Quiz(Base):
    __tablename__ = 'quizzes'

    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    course_id = Column(Integer, ForeignKey('courses.id'))
    subject_id = Column(Integer, ForeignKey('subjects.id'))

    duration = Column(Integer, default=30)
    upload_time = Column(DateTime, default=datetime.utcnow)

    status = Column(String(50), default='inactive')  

    course = relationship('Course', backref='quizzes')
    subject = relationship('Subject', backref='quizzes')
    questions = relationship('Question', cascade='all, delete-orphan', backref='quiz')
    results = relationship('Result', backref='quiz')


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"))

    question_text = Column(Text)
    option_a = Column(Text)
    option_b = Column(Text)
    option_c = Column(Text)
    option_d = Column(Text)
    correct_option = Column(String(1))

    marks = Column(Integer, default=1)  

    image = Column(Text)
    extra_content = Column(Text)    

class Result(Base):
    __tablename__ = 'results'

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('users.id'))
    quiz_id = Column(Integer, ForeignKey('quizzes.id'))
    score = Column(Integer)
    total_marks = Column(Integer)     
    percentage = Column(Float)       
    taken_on = Column(DateTime, default=datetime.utcnow)

class Course(Base):
    __tablename__ = 'courses'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)

    subjects = relationship("Subject", back_populates="course", cascade="all, delete")

class Subject(Base):
    __tablename__ = 'subjects'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    course_id = Column(Integer, ForeignKey('courses.id'))

    course = relationship("Course", back_populates="subjects")