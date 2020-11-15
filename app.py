from flask import Flask, render_template, request, session, redirect, abort
import datetime
from db import init_db, query, insert, delete, close_connection
from sqlite3 import IntegrityError

app = Flask(__name__)
app.secret_key = "4qq2lj0r0a2qvuf2oxzbd4wq7frse279"

def check_auth():
    if "auth" in session:return True
    return False


@app.route('/')
def index():
    init_db()

    if not check_auth(): return redirect("/login")
    return redirect("/dashboard")


@app.route('/login')
def get_login():

    if not check_auth():
        return render_template("auth/login.html", alert=session.pop("alert", None) )
    else:
        return redirect("/dashboard")

@app.route('/login', methods=['POST'])
def post_login():

    def authenticate(username, password):
        auth = query("select first_name,last_name,username from users where username = ? and pw = ?", (username, password), True )
        return auth

    auth = authenticate(request.form["username"], request.form["password"])
    if auth:
        session['auth'] = auth
        session["alert"] = { "level": "success", "message": "Successfully logged in!"}
        return redirect("/dashboard")
    else:
        session["alert"] = {
            "level": "danger", "message": "Login error! Please try again!" }
        return redirect("/login")


@app.route('/logout')
def logout():
    if check_auth(): session.pop("auth", None)
    return redirect("/")

@app.route('/dashboard')
def dashboard():
    if not check_auth(): return redirect("/login")


    breadcrumbs = [{"title": "Dashboard", "url": "/"}]

    students = query("select * from students order by last_name, first_name asc")
    quizzes = query("select * from quizzes order by quiz_date asc")

    return render_template("teacher/dashboard.html", breadcrumbs=breadcrumbs, students=students, quizzes=quizzes, alert=session.pop("alert", None) )


@app.route('/student/add')
def get_add_student():
    if not check_auth(): return redirect("/login")


    breadcrumbs = [ {"title": "Dashboard", "url": "/dashboard"}, {"title": "Add Student", "url": "/student/add"} ]

    return render_template("teacher/add_student.html", breadcrumbs=breadcrumbs, errors=session.pop("errors", None), alert=session.pop("alert", None) )


@app.route('/student/add', methods=['POST'])
def post_add_student():
    if not check_auth(): return redirect("/login")

    def validate(form):

        validation_errors = {"messages": {}, "input": {}}

        if (form["first_name"].strip() == ""):
            validation_errors["messages"].update({"first_name": "First name is a required field."})

        if (form["last_name"].strip() == ""):
            validation_errors["messages"].update({"last_name": "Last name is a required field."})

        if validation_errors["messages"]: validation_errors.update({"input": dict(form)})
        else: validation_errors = {}

        return validation_errors

    validation = validate(request.form)
    if not validation:
        row_id = insert("Insert into students (first_name, last_name) values (?, ?)", (request.form["first_name"], request.form["last_name"]))
        session["alert"] = { "level": "success", "message": "Student added successfully!" }
        return redirect("/dashboard#student-"+str(row_id))
    else:
        session["errors"] = validation        
        return redirect("/student/add")


@app.route('/student/<id>')
def get_student(id):
    if not check_auth(): return redirect("/login")

    student = query("select * from students where id = ?", (id, ), True)

    if not student:
        session["alert"] = { "level": "danger", "message": "Could not find a student with ID # {}.". format(str(id))}
        return redirect("/dashboard")

    quizzes = query("select q.*, sq.score from quizzes q inner join student_quiz sq on sq.student_id = ? and sq.quiz_id = q.id order by quiz_date asc", (id, ))

    breadcrumbs = [ {"title": "Dashboard", "url": "/dashboard"}, {"title": "Student", "url": "/student/"+id}]
    return render_template("teacher/view_student.html", breadcrumbs=breadcrumbs, student=student, quizzes=quizzes, alert=session.pop("alert", None) )


@app.route('/student/<id>/delete', methods=['POST'])
def post_delete_student(id):
    if not check_auth(): return redirect("/login")

    student = query("select * from students where id = ?", (id, ), True)

    if not student:
        session["alert"] = { "level": "danger", "message": "Could not find a student with ID # {}." .format(str(id)) }
        return redirect("/dashboard")

    delete("delete from student_quiz where student_id = ?", (id, ))
    delete("delete from students where id = ?", (id, ))

    session["alert"] = { "level": "success", "message": "Deleted student and quiz results for student ID # {} successfully.".format(str(id))}
    return redirect("/dashboard")


@app.route('/quiz/add')
def get_add_quiz():
    if not check_auth(): return redirect("/login")

    breadcrumbs = [ {"title": "Dashboard", "url": "/dashboard"}, {"title": "Add Quiz", "url": "/quiz/add"}]
    return render_template("teacher/add_quiz.html", breadcrumbs=breadcrumbs, errors=session.pop("errors", None), alert=session.pop("alert", None))


@app.route('/quiz/add', methods=['POST'])
def post_add_quiz():
    if not check_auth(): return redirect("/login")

    def validate(form):
        
        validation_errors = {"messages": {}, "input": {}}
        
        if (form["quiz_subject"].strip() == ""):
            validation_errors["messages"].update({"quiz_subject": "Quiz Subject is a required field."})

        if (form["question_count"].strip() == ""):
            validation_errors["messages"].update({"question_count": "# of Questions is a required field."})
        else:
            try:
               if int(form["question_count"]) < 0: raise ValueError
            except ValueError:
                validation_errors["messages"].update({"question_count": "Please enter a valid number."})

        if (form["quiz_date"].strip() == ""):
            validation_errors["messages"].update({"quiz_date": "Quiz Date is a required field."})
        else:
            try:
                datetime.datetime.strptime(form["quiz_date"], '%Y-%m-%d')
            except ValueError:
                validation_errors["messages"].update({"quiz_date": "A date in YYYY-MM-DD format is required."})

        if validation_errors["messages"]: validation_errors.update({"input": dict(form)})
        else: validation_errors = {}

        return validation_errors

    validation = validate(request.form)
    if not validation:
        row_id = insert("Insert into quizzes (quiz_subject, question_count, quiz_date) values (?, ?, ?)", (request.form["quiz_subject"], request.form["question_count"],request.form["quiz_date"]))

        session["alert"] = {"level": "success","message": "Quiz added successfully!"}

        return redirect("/dashboard#quiz-"+str(row_id))
    else:
        session["errors"] = validation
        return redirect("/quiz/add")


@app.route('/quiz/<id>/delete', methods=['POST'])
def post_delete_quiz(id):
    if not check_auth():return redirect("/login")

    quiz = query("select * from quizzes where id = ?", (id, ), True)

    if not quiz:
        session["alert"] = {"level": "danger","message": "Could not find a quiz with ID # {}.".format(str(id))}
        return redirect("/dashboard")

    delete("delete from student_quiz where quiz_id = ?", (id, ))
    delete("delete from quizzes where id = ?", (id, ))

    session["alert"] = {"level": "success", "message": "Deleted quiz and results for quiz ID # {} successfully.".format(str(id))}
    return redirect("/dashboard")


@app.route('/quiz/<id>/results')
def get_quiz_results(id):
    authed = check_auth()

    quiz = query("select * from quizzes where id = ?", (id, ), True)

    if not quiz:
        if authed:
            session["alert"] = { "level": "danger", "message": "Could not find a quiz with ID # {}.".format(str(id))}
            return redirect("/dashboard")
        else:
            abort(404)

    results = query("select s.*, sq.score from students s inner join student_quiz sq on sq.quiz_id = ? and sq.student_id = s.id order by last_name, first_name asc", (id, ))

    breadcrumbs = [ {"title": "Dashboard", "url": "/dashboard"}, {"title": "Quiz Results", "url": "/quiz/"+id+"/results"}] if authed else []
    
    return render_template("shared/view_results.html", breadcrumbs=breadcrumbs, quiz=quiz, results=results, authed=authed, alert=session.pop("alert", None) )


@app.route('/quiz/<quiz_id>/results/<student_id>/delete', methods=['POST'])
def get_delete_quiz_result(quiz_id, student_id):
    result = query("select * from student_quiz where quiz_id = ? and student_id = ?", (quiz_id, student_id), True)

    if not result:
        session["alert"] = {"level": "danger","message": "Could not find a result for quiz ID # {} and student ID # {}.".format(str(quiz_id), str(student_id))}
        return redirect("/dashboard")

    delete("delete from student_quiz where quiz_id = ? and student_id = ?", (quiz_id, student_id))

    session["alert"] = {"level": "success","message": "Deleted quiz result successfully."}
    return redirect("/dashboard")


@app.route('/results/add')
def get_add_result():
    breadcrumbs = [{"title": "Dashboard", "url": "/dashboard"},{"title": "Add Quiz Result", "url": "/results/add"}]

    students = query("select * from students order by last_name, first_name asc")
    quizzes = query("select * from quizzes order by quiz_date asc")

    return render_template("teacher/add_result.html", breadcrumbs=breadcrumbs, students=students, quizzes=quizzes, errors=session.pop("errors", None), alert=session.pop("alert", None) )


@app.route('/results/add', methods=['POST'])
def post_add_result():
    def validate(form):
        validation_errors = {"messages": {}, "input": {}}

        if (form["student_id"].strip() == ""): validation_errors["messages"].update( {"student_id": "Please select a student from the list."})
        else:
            try:
               int(form["student_id"])
            except ValueError:
                validation_errors["messages"].update({"student_id": "Please select a student from the list."})

        if (form["quiz_id"].strip() == ""):
            validation_errors["messages"].update({"quiz_id": "Please select a quiz from the list."})
        else:
            try:
               int(form["quiz_id"])
            except ValueError:
                validation_errors["messages"].update({"quiz_id": "Please select a quiz from the list."})

        if (form["score"].strip() == ""):
            validation_errors["messages"].update({"score": "Grade is a required field."})
        else:
            try:
               score = int(form["score"])
               if score < 0 or score > 100:
                   raise ValueError
            except ValueError:
                validation_errors["messages"].update({"score": "Please enter a number between 0 and 100."})

        if validation_errors["messages"]:
            validation_errors.update({"input": dict(form)})
        else:
            validation_errors = {}

        return validation_errors

    validation = validate(request.form)
    if not validation:
        try:
            insert("Insert into student_quiz (student_id, quiz_id, score) values (?, ?, ?)", (request.form["student_id"], request.form["quiz_id"], request.form["score"]))

            session["alert"] = { "level": "success", "message": "Quiz result added for student ID # {} successfully!" .format(request.form["student_id"]) }

            return redirect("/dashboard")

        except IntegrityError:
            session["alert"] = {
                "level": "danger",
                "message": "Quiz result could not be added for \
                            quiz ID # {} and student ID # {} because \
                            an entry already exists. Delete the current \
                            quiz result for the student first."
                .format(request.form["quiz_id"],
                        request.form["student_id"])
            }

            return redirect("/dashboard")

    else:
        session["errors"] = validation
        return redirect("/results/add")


@app.teardown_appcontext
def teardown(exception):
    close_connection(exception)


if __name__ == '__main__':
    app.run()
