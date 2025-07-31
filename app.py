from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import User,StudentProfile,Course,Quiz,Result,Subject,Question
from connection import SessionLocal
from werkzeug.utils import secure_filename
import os
from utils import parse_docx_questions
from datetime import datetime
from sqlalchemy.orm import joinedload
import io
import csv
from flask import Response
from utils import get_quiz_status

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
    return redirect ('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = False  # Default: no error

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
                error = True  # Incorrect credentials
        finally:
            db.close()

    return render_template('login.html', error=error)


#--------------student dashboard ----------------
@app.route('/student/dashboard')
def student_dashboard():
    if 'username' not in session or session.get('role') != 'student':
        flash('Please log in as a student first.', 'error')
        return redirect(url_for('login'))

    db = SessionLocal()
    try:
        # Fetch user
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

   
        available_quizzes = db.query(Quiz).filter_by(course_id=student_profile.course_id).all()

      
        results = db.query(Result).join(Quiz).options(
            joinedload(Result.quiz).joinedload(Quiz.subject)
        ).filter(Result.student_id == user.id).all()

       
        return render_template(
            'student/student_dashboard.html',
            profile=student_profile,
            quizzes=available_quizzes,
            results=results,
            course_name=course_name,
            year=datetime.utcnow().year
        )

    finally:
        db.close()
#______________admin dashboard__________________
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required. Please log in.', 'error')
        return redirect(url_for('login'))

    db = SessionLocal()
    try:
        courses = db.query(Course).all()
        quizzes = db.query(Quiz).options(
            joinedload(Quiz.course),
            joinedload(Quiz.subject)
        ).order_by(Quiz.upload_time.desc()).all()
    finally:
        db.close()

    return render_template('admin/admin_dashboard.html', courses=courses, quizzes=quizzes)

'-----------new student kinldy register-----------------'
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Create a session instance
        db = SessionLocal()
        try:
            # Check if username already exists
            existing_user = db.query(User).filter_by(username=username).first()
            if existing_user:
                flash('Username already exists, please choose another one.', 'danger')
                return redirect(url_for('register'))

            # Create and add the new user
            new_user = User(username=username, password=password, role='student')
            db.add(new_user)
            db.commit()

            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        finally:
            db.close()

    return render_template('student/register.html')
#--------------------new student complete your profile please---------------'
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

    return render_template(
        'student/complete_profile.html',
        courses=courses,
        student_profile=student_profile
    )
@app.route('/student/take_exam/<int:quiz_id>', methods=['GET', 'POST'])
def take_exam(quiz_id):
    if 'username' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))

    db = SessionLocal()
    try:
        quiz = db.query(Quiz).filter_by(id=quiz_id).first()

        if not quiz or quiz.status != 'active':
            flash('This exam is not available.', 'danger')
            return redirect(url_for('student_dashboard'))

        # Prevent retakes
        existing_result = db.query(Result).filter_by(
            student_id=session['user_id'], quiz_id=quiz_id).first()
        if existing_result:
            flash('You have already taken this exam.', 'warning')
            return redirect(url_for('student_dashboard'))

        questions = db.query(Question).filter_by(quiz_id=quiz_id).all()

        if request.method == 'POST':
            total_raw_marks = sum(q.marks for q in questions)
            score_raw = 0

            for question in questions:
                answer = request.form.get(f'question_{question.id}')
                if answer and answer.strip().lower() == question.correct_option.strip().lower():
                    score_raw += question.marks

            # Scale score to 50
            if total_raw_marks > 0:
                score = (score_raw / total_raw_marks) * 50
                percentage = (score / 50) * 100
            else:
                score = 0
                percentage = 0

            result = Result(
                student_id=session['user_id'],
                quiz_id=quiz_id,
                score=round(score, 2),
                total_marks=50,
                percentage=round(percentage, 2)
            )

            db.add(result)
            db.commit()
            db.refresh(result)

            flash(f'Exam submitted successfully. Your result: {round(score,2)}/50 ({round(percentage,2)}%)', 'success')
            return redirect(url_for('view_result', result_id=result.id))

        return render_template('student/take_exam.html', quiz=quiz, questions=questions,uration_minutes=quiz.duration)

    finally:
        db.close()


#-----------------student to view their results------------------------------------
@app.route('/student/result/<int:result_id>')
def view_result(result_id):
    if 'user_id' not in session or session.get('role') != 'student':
        flash('Please log in as a student.', 'warning')
        return redirect(url_for('login'))

    db = SessionLocal()

    try:
        result = db.query(Result).filter_by(id=result_id, student_id=session['user_id']).first()

        if not result:
            flash('Result not found or unauthorized access.', 'danger')
            return redirect(url_for('student_dashboard'))

        return render_template('student/view_result.html', result=result)

    except Exception as e:
        flash(f'Error loading result: {str(e)}', 'danger')
        return redirect(url_for('student_dashboard'))

    finally:
        db.close()


#------student submit results route--------------------------------
@app.route('/submit_exam/<quiz_id>', methods=['POST'])
def submit_exam(quiz_id):
    if 'username' not in session:
        flash('Please log in first.', 'error')
        return redirect(url_for('login'))

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(username=session['username']).first()
        student_profile = user.profile

   
        if not student_profile:
            flash("Complete your profile before proceeding.", "warning")
            return redirect(url_for('complete_profile'))

    
        quiz = db.query(Quiz).filter_by(id=quiz_id).first()

        if not quiz:
            flash("Quiz not found.", "danger")
            return redirect(url_for('student_dashboard'))

     
        answers = request.form

        total_score = 0
        total_marks = 0

    
        for question in quiz.questions:
            question_answer = answers.get(str(question.id))
            if question_answer == question.correct_option:
                total_score += question.marks
            total_marks += question.marks

   
        percentage = (total_score / total_marks) * 100 if total_marks else 0

       
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

        return redirect(url_for('student_dashboard'))
    except Exception as e:
        db.rollback()
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('student_dashboard'))
    finally:
        db.close()

'________________Admin upload exams___________________________'
@app.route('/admin/upload_exam', methods=['GET', 'POST'])
def upload_exam():
    db = SessionLocal()

    # Load dropdown options for courses and subjects
    courses = db.query(Course).all()
    subjects = db.query(Subject).all()

    if request.method == 'POST':
        title = request.form.get('title')
        course_id = request.form.get('course')
        subject_id = request.form.get('subject')
        duration = request.form.get('duration')
        file = request.files.get('quiz_file')

        # Validate uploaded file
        if not file or not allowed_file(file.filename):
            flash('❌ Please upload a valid .docx file.', 'danger')
            db.close()
            return redirect(request.url)

        # Save file securely
        filename = secure_filename(file.filename)
        upload_dir = os.path.join(os.getcwd(), 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        # Parse .docx file
        try:
            with open(file_path, 'rb') as f:
                questions_data = parse_docx_questions(f)
        except Exception as e:
            flash(f"❌ Failed to parse file: {str(e)}", "danger")
            db.close()
            return redirect(request.url)

        if not questions_data:
            flash("❌ No valid questions found in the document.", "danger")
            db.close()
            return redirect(request.url)

        # Create a new quiz record
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
        db.refresh(quiz)  # Get the new quiz.id

        # Save each question from the .docx file
        saved_count = 0
        for q in questions_data:
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
        db.close()
        return redirect(url_for('upload_exam'))

    db.close()
    return render_template('admin/upload_exams.html', courses=courses, subjects=subjects)

#_________admin can add a course ____________________
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

#___________________admin can edit a course_________________
@app.route('/admin/edit_course/<int:course_id>', methods=['GET', 'POST'])
def edit_course(course_id):
    # Check if the user is logged in as an admin
    if 'user_id' not in session or session['role'] != 'admin':
        flash('You must be logged in as an admin to access this page.', 'danger')
        return redirect(url_for('login'))  # Redirect to login if not an admin

    # Fetch the course by its ID
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

#_________________admin can delete a course___________________
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

#________________admin add subject management______________
@app.route('/admin/add_subject', methods=['GET', 'POST'])
def add_subject():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('You must be logged in as an admin to access this page.', 'danger')
        return redirect(url_for('login'))  # Redirect to login if not an admin

    db = SessionLocal()  # Creating the database session

    if request.method == 'POST':
        subject_name = request.form.get('subject_name')

        if subject_name:
            # Check if the subject already exists
            existing_subject = db.query(Subject).filter_by(name=subject_name).first()
            if existing_subject:
                flash(f'Subject "{subject_name}" already exists.', 'danger')
            else:
                # Create and add the new subject
                new_subject = Subject(name=subject_name)
                db.add(new_subject)
                db.commit()
                flash(f'Subject "{subject_name}" added successfully!', 'success')
                return redirect(url_for('admin_dashboard'))  # Redirect to dashboard after successful subject addition
        else:
            flash('Subject name cannot be empty.', 'danger')

    db.close()  # Close the session
    return render_template('admin/add_subject.html')

#_______________VIEW _______________

@app.route('/admin/results', methods=['GET', 'POST'])
def admin_results():
    if session.get('role') != 'admin':
        return redirect('/login')

    db = SessionLocal()

    # Fetch courses and subjects for the dropdown
    courses = db.query(Course).all()
    subjects = db.query(Subject).all()

    # Filter options
    selected_course = request.form.get('course')
    selected_subject = request.form.get('subject')
    export = request.form.get('export')

    # Base query for results
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

    # Handle CSV export
    if export == 'true':
        import io
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write CSV header
        writer.writerow(['Student ID', 'Full Name', 'Course', 'Subject', 'Quiz Title', 'Score', 'Total Marks', '%Percentage', 'Taken On'])
        
        # Write data rows
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


#_____________manage student____________________________

@app.route('/admin/manage_students')
def manage_students():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('You must be logged in as an admin to access this page.', 'danger')
        return redirect(url_for('login'))

    db = SessionLocal()
    try:
        # Get all users with role 'student'
        students = db.query(User).filter_by(role='student').all()
        return render_template('admin/manage_students.html', students=students)
    finally:
        db.close()

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('login'))

#-----------admin delete ----
@app.route('/admin/delete_quiz/<int:quiz_id>', methods=['POST'])
def delete_quiz(quiz_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Admin access required.', 'error')
        return redirect(url_for('login'))

    db = SessionLocal()
    try:
        quiz = db.query(Quiz).filter_by(id=quiz_id).first()
        if quiz:
            db.delete(quiz)
            db.commit()
            flash(f'Quiz "{quiz.title}" has been deleted.', 'success')
        else:
            flash('Quiz not found.', 'error')
    except Exception as e:
        db.rollback()
        flash(f'An error occurred: {e}', 'error')
    finally:
        db.close()

    return redirect(url_for('admin_dashboard'))
    
if __name__ == "__main__":
    app.run(debug=True)