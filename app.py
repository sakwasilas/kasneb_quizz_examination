from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from models import User, StudentProfile, Course, Quiz, Result, Subject, Question
from connection import SessionLocal
from werkzeug.utils import secure_filename
from utils import parse_docx_questions, get_quiz_status
from datetime import datetime
from sqlalchemy.orm import joinedload
import os
import io
import csv

app = Flask(__name__)
app.secret_key = '00025000000000000'

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = False
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        db = SessionLocal()
        try:
            user = db.query(User).filter_by(username=username).first()
            if user and user.password == password:
                session['username'] = user.username
                session['user_id'] = user.id
                session['role'] = user.role
                if user.role == 'student':
                    return redirect(url_for('student_dashboard'))
                else:
                    return redirect(url_for('admin_dashboard'))
            else:
                error = True
        finally:
            db.close()
    return render_template('login.html', error=error)

@app.route('/student/dashboard')
def student_dashboard():
    if 'username' not in session or session.get('role') != 'student':
        flash('Please log in as a student first.', 'error')
        return redirect(url_for('login'))

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(username=session['username']).first()
        if not user:
            flash("User not found.", "error")
            return redirect(url_for('logout'))

        student_profile = db.query(StudentProfile).options(
            joinedload(StudentProfile.course)
        ).filter_by(user_id=user.id).first()

        if not student_profile:
            flash("Complete your profile before proceeding.", "warning")
            return redirect(url_for('complete_profile'))

        course_name = student_profile.course.name if student_profile.course else ''

        # ✅ Only show active quizzes
        available_quizzes = db.query(Quiz).filter_by(
            course_id=student_profile.course_id,
            status='active'
        ).all()

        # ✅ Get completed quizzes (i.e., results)
        completed_results = db.query(Result).filter_by(student_id=user.id).all()
        completed_quiz_ids = [result.quiz_id for result in completed_results]

        # ✅ Prepare results for table display
        results = []
        for result in completed_results:
            percentage = (result.score / result.total_marks) * 100 if result.total_marks else 0
            results.append({
                'quiz': result.quiz,
                'score': result.score,
                'total_marks': result.total_marks,
                'percentage': round(percentage, 2)
            })

        return render_template(
            'student/student_dashboard.html',
            profile=student_profile,
            quizzes=available_quizzes,
            results=results,
            course_name=course_name,
            completed_quiz_ids=completed_quiz_ids,
            year=datetime.utcnow().year
        )
    finally:
        db.close()
# -------------------- Admin Dashboard --------------------
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('You must be logged in as an admin to access this page.', 'danger')
        return redirect(url_for('login'))

    db = SessionLocal()
    try:
        
        courses = db.query(Course).all()
        quizzes = db.query(Quiz).all()
        student_count = db.query(User).filter_by(role='student').count()
        return render_template('admin/admin_dashboard.html', courses=courses, quizzes=quizzes, student_count=student_count)
    finally:
        db.close()

# -------------------- Student Registration --------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = SessionLocal()
        try:
            existing_user = db.query(User).filter_by(username=username).first()
            if existing_user:
                flash('Username already exists, please choose another one.', 'danger')
                return redirect(url_for('register'))

            new_user = User(username=username, password=password, role='student')
            db.add(new_user)
            db.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        finally:
            db.close()
    return render_template('student/register.html')

# -------------------- Complete Student Profile --------------------
@app.route('/complete_profile', methods=['GET', 'POST'])
def complete_profile():
    if 'user_id' not in session or session.get('role') != 'student':
        flash('Please log in as a student.', 'warning')
        return redirect(url_for('login'))

    user_id = session['user_id']
    db = SessionLocal()

    student_profile = None
    courses = []

    try:
        student_profile = db.query(StudentProfile).filter_by(user_id=user_id).first()
        courses = db.query(Course).all()

        if request.method == 'POST':
            full_name = request.form.get('full_name')
            course_id = request.form.get('course_id')
            level = request.form.get('level')
            kasneb_no = request.form.get('kasneb_no')

            if student_profile:
                student_profile.full_name = full_name
                student_profile.course_id = course_id
                student_profile.level = level
                student_profile.kasneb_no = kasneb_no
                student_profile.profile_completed = True
            else:
                student_profile = StudentProfile(
                    user_id=user_id,
                    full_name=full_name,
                    course_id=course_id,
                    level=level,
                    kasneb_no=kasneb_no,
                    profile_completed=True
                )
                db.add(student_profile)

            db.commit()
            flash('Profile updated successfully.', 'success')
            return redirect(url_for('student_dashboard'))

    except Exception as e:
        db.rollback()
        flash(f'Error updating profile: {str(e)}', 'danger')

    finally:
        db.close()

    return render_template('student/complete_profile.html', courses=courses, student_profile=student_profile)

# -------------------- Take Exam --------------------
@app.route('/student/take_exam/<int:quiz_id>', methods=['GET', 'POST'])
def take_exam(quiz_id):
    if 'username' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))

    db = SessionLocal()
    try:
        # Fetch the quiz and its subject
        quiz = db.query(Quiz).filter_by(id=quiz_id).first()
        if not quiz or quiz.status != 'active':
            flash('This exam is not available.', 'danger')
            return redirect(url_for('student_dashboard'))

        # Check if the student has already taken the quiz
        existing_result = db.query(Result).filter_by(student_id=session['user_id'], quiz_id=quiz_id).first()
        if existing_result:
            flash('You have already taken this exam.', 'warning')
            return redirect(url_for('student_dashboard'))  # Redirect to dashboard if already taken

        questions = db.query(Question).filter_by(quiz_id=quiz_id).order_by(Question.id.asc()).all()

        if not questions:
            flash('No questions available for this quiz.', 'danger')
            return redirect(url_for('student_dashboard'))

        # Ensure you're passing the subject name as a string
        subject_name = quiz.subject.name if quiz.subject else 'No Subject'

        return render_template(
            'student/take_exam.html',
            quiz=quiz,
            questions=questions,
            subject_name=subject_name,  # Pass the subject name to the template
            duration_minutes=quiz.duration
        )
    finally:
        db.close()
@app.route('/submit_exam/<quiz_id>', methods=['POST'])
def submit_exam(quiz_id):
    if 'username' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(username=session['username']).first()
        quiz = db.query(Quiz).filter_by(id=quiz_id).first()

        answers = request.form
        total_score = 0
        total_marks = 0

        # Calculate score based on selected answers
        for question in quiz.questions:
            question_answer = answers.get(f"q{question.id}")
            if question_answer == question.correct_option:
                total_score += question.marks
            total_marks += question.marks

        # Calculate percentage
        percentage = (total_score / total_marks) * 100 if total_marks else 0

        # Save result in the database
        result = Result(
            student_id=user.id,
            quiz_id=quiz.id,
            score=total_score,
            total_marks=total_marks,
            percentage=percentage
        )

        db.add(result)
        db.commit()

        flash(f'You scored {total_score} out of {total_marks} ({percentage}%)', 'success')

        # Redirect to the result page (results view)
        return redirect(url_for('exam_results', quiz_id=quiz.id))  # Redirect to the result page

    except Exception as e:
        db.rollback()  # In case of any error, rollback the transaction
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('student_dashboard'))  # Redirect to the dashboard on error

    finally:
        db.close()
# -------------------- Admin Upload Exam --------------------
@app.route('/admin/upload_exam', methods=['GET', 'POST'])
def upload_exam():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('You must be logged in as an admin to access this page.', 'danger')
        return redirect(url_for('login'))

    db = SessionLocal()
    courses = db.query(Course).all()
    subjects = db.query(Subject).all()

    if request.method == 'POST':
        title = request.form.get('title')
        course_id = request.form.get('course')
        subject_id = request.form.get('subject')
        duration = request.form.get('duration')
        file = request.files.get('quiz_file')

        if not file or not allowed_file(file.filename):
            flash('❌ Please upload a valid .docx file.', 'danger')
            return redirect(request.url)

        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        try:
            with open(file_path, 'rb') as f:
                # Parsing the questions from the uploaded .docx file
                questions_data = parse_docx_questions(f)

            if not questions_data:  # Assuming questions_data is a list
                flash("❌ No valid questions found in the document.", "danger")
                return redirect(request.url)

            quiz = Quiz(
                title=title,
                course_id=int(course_id),
                subject_id=int(subject_id),
                duration=int(duration),
                status='active',
                upload_time=datetime.utcnow()
            )
            db.add(quiz)
            db.commit()
            db.refresh(quiz)

            saved_count = 0
            for q in questions_data:  # If it's a list, directly loop over it
                question = Question(
                    quiz_id=quiz.id,
                    question_text=q.get("question", ""),
                    option_a=q.get("a", ""),
                    option_b=q.get("b", ""),
                    option_c=q.get("c", ""),
                    option_d=q.get("d", ""),
                    correct_option=q.get("answer", "").lower(),
                    marks=q.get("marks", 1),
                    extra_content=q.get("extra_content"),
                    image=q.get("image")
                )
                db.add(question)
                saved_count += 1

            db.commit()
            flash(f"✅ Uploaded quiz successfully with {saved_count} question(s).", "success")
            return redirect(url_for('upload_exam'))

        except Exception as e:
            flash(f"❌ Failed to parse file: {str(e)}", "danger")
            return redirect(request.url)

    db.close()
    return render_template('admin/upload_exams.html', courses=courses, subjects=subjects)

# -------------------- Admin Add Course --------------------
@app.route('/admin/add_course', methods=['GET', 'POST'])
def add_course():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('You must be logged in as an admin to access this page.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        course_name = request.form.get('course_name')
        if course_name:
            db = SessionLocal()
            new_course = Course(name=course_name)
            db.add(new_course)
            db.commit()
            db.close()
            flash('Course added successfully!', 'success')
            return redirect(url_for('admin_dashboard'))

    return render_template('admin/add_course.html')

# -------------------- Admin Edit Course --------------------
@app.route('/admin/edit_course/<int:course_id>', methods=['GET', 'POST'])
def edit_course(course_id):
    if 'user_id' not in session or session['role'] != 'admin':
        flash('You must be logged in as an admin to access this page.', 'danger')
        return redirect(url_for('login'))

    db = SessionLocal()
    course = db.query(Course).filter_by(id=course_id).first()

    if not course:
        flash('Course not found', 'danger')
        db.close()
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        course_name = request.form.get('course_name')
        if course_name:
            course.name = course_name
            db.commit()
            db.close()
            flash('Course updated successfully!', 'success')
            return redirect(url_for('admin_dashboard'))

    db.close()
    return render_template('admin/edit_course.html', course=course)

# -------------------- Admin Delete Course --------------------
@app.route('/admin/delete_course/<int:course_id>', methods=['GET'])
def delete_course(course_id):
    if 'user_id' not in session or session['role'] != 'admin':
        flash('You must be logged in as an admin to access this page.', 'danger')
        return redirect(url_for('login'))

    db = SessionLocal()
    course = db.query(Course).filter_by(id=course_id).first()

    if course:
        try:
            db.delete(course)
            db.commit()
            flash(f'Course "{course.name}" deleted successfully!', 'success')
        except Exception as e:
            db.rollback()
            flash(f'Error deleting course: {str(e)}', 'danger')
    else:
        flash('Course not found', 'danger')

    db.close()
    return redirect(url_for('admin_dashboard'))

# -------------------- Admin Add Subject --------------------
@app.route('/admin/add_subject', methods=['GET', 'POST'])
def add_subject():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('You must be logged in as an admin to access this page.', 'danger')
        return redirect(url_for('login'))

    db = SessionLocal()
    if request.method == 'POST':
        subject_name = request.form.get('subject_name')

        if subject_name:
            existing_subject = db.query(Subject).filter_by(name=subject_name).first()
            if existing_subject:
                flash(f'Subject "{subject_name}" already exists.', 'danger')
            else:
                new_subject = Subject(name=subject_name)
                db.add(new_subject)
                db.commit()
                flash(f'Subject "{subject_name}" added successfully!', 'success')
                return redirect(url_for('admin_dashboard'))
        else:
            flash('Subject name cannot be empty.', 'danger')

    db.close()
    return render_template('admin/add_subject.html')

# -------------------- Admin View Results --------------------
@app.route('/admin/results', methods=['GET', 'POST'])
def admin_results():
    if session.get('role') != 'admin':
        return redirect('/login')

    db = SessionLocal()
    courses = db.query(Course).all()
    subjects = db.query(Subject).all()

    selected_course = request.form.get('course')
    selected_subject = request.form.get('subject')
    export = request.form.get('export')

    query = db.query(Result).join(Result.quiz).join(Quiz.course).join(Quiz.subject).options(
        joinedload(Result.quiz).joinedload(Quiz.subject),
        joinedload(Result.student).joinedload(User.profile),
        joinedload(Result.quiz).joinedload(Quiz.course),
        joinedload(Result.student)
    )

    if selected_course:
        query = query.filter(Quiz.course_id == int(selected_course))
    if selected_subject:
        query = query.filter(Quiz.subject_id == int(selected_subject))

    results = query.all()

    if export == 'true':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Student ID', 'Full Name', 'Course', 'Subject', 'Quiz Title', 'Score', 'Total Marks', '%Percentage', 'Taken On'])

        for r in results:
            writer.writerow([
                r.student.username if r.student else 'N/A',
                r.student.profile.full_name if r.student and r.student.profile else 'N/A',
                r.quiz.course.name if r.quiz and r.quiz.course else 'N/A',
                r.quiz.subject.name if r.quiz and r.quiz.subject else 'N/A',
                r.quiz.title if r.quiz else 'N/A',
                r.score,
                r.total_marks,
                r.percentage,
                r.taken_on.strftime("%Y-%m-%d %H:%M:%S")
            ])

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=results.csv"}
        )

    db.close()
    return render_template('admin/admin_results.html',
                           courses=courses,
                           subjects=subjects,
                           results=results,
                           selected_course=selected_course,
                           selected_subject=selected_subject)

# -------------------- Admin Manage Students --------------------
@app.route('/admin/manage_students')
def manage_students():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('You must be logged in as an admin to access this page.', 'danger')
        return redirect(url_for('login'))

    db = SessionLocal()
    try:
        students = db.query(User).filter_by(role='student').all()
        return render_template('admin/manage_students.html', students=students)
    finally:
        db.close()

#---------------------activate or deactivate quizz----------
@app.route('/admin/toggle_quiz_status/<int:quiz_id>', methods=['POST'])
def toggle_quiz_status(quiz_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    db = SessionLocal()
    try:
        quiz = db.query(Quiz).filter_by(id=quiz_id).first()
        if quiz:
            quiz.status = 'active' if quiz.status == 'inactive' else 'inactive'
            db.commit()
        return redirect(url_for('admin_dashboard'))
    finally:
        db.close()
#__________results___________________
@app.route('/exam_results/<quiz_id>', methods=['GET'])
def exam_results(quiz_id):
    if 'username' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(username=session['username']).first()
        result = db.query(Result).filter_by(student_id=user.id, quiz_id=quiz_id).first()

        if not result:
            flash("No result found for this exam.", "warning")
            return redirect(url_for('student_dashboard'))

        return render_template('student/exam_results.html', result=result)

    finally:
        db.close()

# -------------------- Logout --------------------
@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

# -------------------- Run App --------------------
if __name__ == "__main__":
    app.run(debug=True)