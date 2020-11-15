import sqlite3
from flask import current_app, g

DATABASE = 'hw13.db'

def make_dicts(cursor, row):
    return dict((cursor.description[idx][0], value) for idx, value in enumerate(row))

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = make_dicts
    return db

def query(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def insert(query, vals=(), many=False):
    if many:
        cur = get_db().executemany(query, vals)
    else:
        cur = get_db().execute(query, vals)

    last_row_id = cur.lastrowid
    cur.close()
    get_db().commit()
    return last_row_id


def delete(query, vals=()):
    cur = get_db().execute(query, vals)
    cur.close()
    get_db().commit()
    return True

def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None: db.close()


def init_db():
    db = get_db()

    with current_app.open_resource('schema.sql') as f: db.executescript(f.read().decode('utf8'))

    students = query("select * from students")
    quizzes = query("select * from quizzes")
    quiz_results = query("select * from student_quiz")
    users = query("select * from users")

    if not students: insert("Insert into students values (?, ?, ?)",(1001, "John", "Smith"))

    if not quizzes: insert("Insert into quizzes values (?, ?, ?, ?)", (1, "Python Basics", 5, "2015-02-05"))

    if not quiz_results: insert("Insert into student_quiz values (?, ?, ?)",(1001, 1, 85))

    if not users: insert("Insert into users values (?, ?, ?, ?, ?)",(1, "Teacher", "Admin", "admin", "password"))
