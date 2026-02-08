from flask import Flask, request, redirect, session, send_file
import sqlite3, time, random
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment

app = Flask(__name__)
app.secret_key = "technospectrum_2k26"

# ---------------- DATABASE ----------------
def db():
    return sqlite3.connect("quiz.db", check_same_thread=False)

con = db()
cur = con.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS participants(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT,
 email TEXT UNIQUE,
 contact TEXT,
 score INTEGER,
 start REAL,
 end REAL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS questions(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 q TEXT,
 a TEXT,
 b TEXT,
 c TEXT,
 d TEXT,
 correct TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS settings(
 id INTEGER PRIMARY KEY,
 timer INTEGER
)
""")

if cur.execute("SELECT COUNT(*) FROM settings").fetchone()[0] == 0:
    cur.execute("INSERT INTO settings(id,timer) VALUES(1,60)")
    con.commit()

# ---------------- HELPERS ----------------
def get_timer():
    return cur.execute("SELECT timer FROM settings WHERE id=1").fetchone()[0]

def page(body):
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{{background:linear-gradient(135deg,#667eea,#764ba2);color:white}}
.card{{border-radius:20px;color:black}}
.timer{{background:#6f42c1;color:white;padding:10px;text-align:center}}
.container{{max-width:650px}}
</style>
</head>
<body>
<div class="container mt-4">
<h2 class="text-center">Technospectrum 2K26</h2>
<div class="card p-4 shadow mt-3">
{body}
</div>
</div>
</body>
</html>
"""

# ---------------- USER ----------------
@app.route("/", methods=["GET","POST"])
def register():
    if request.method == "POST":
        try:
            cur.execute(
                "INSERT INTO participants(name,email,contact,start) VALUES(?,?,?,?)",
                (request.form["name"], request.form["email"],
                 request.form["contact"], time.time())
            )
            con.commit()
            session["pid"] = cur.lastrowid
            return redirect("/quiz")
        except:
            return page("<h4>Email already used</h4>")

    return page("""
<form method="post">
<input class="form-control mb-2" name="name" placeholder="Full Name" required>
<input class="form-control mb-2" name="email" placeholder="Email" required>
<input class="form-control mb-2" name="contact" placeholder="Contact Number" required>
<button class="btn btn-primary w-100">Start Quiz</button>
</form>
""")

@app.route("/quiz")
def quiz():
    if "pid" not in session:
        return redirect("/")

    timer = get_timer()
    qs = cur.execute("SELECT * FROM questions").fetchall()
    random.shuffle(qs)

    qhtml = ""
    for q in qs:
        qhtml += f"""
<b>{q[1]}</b><br>
<label><input type="radio" name="{q[0]}" value="a"> {q[2]}</label><br>
<label><input type="radio" name="{q[0]}" value="b"> {q[3]}</label><br>
<label><input type="radio" name="{q[0]}" value="c"> {q[4]}</label><br>
<label><input type="radio" name="{q[0]}" value="d"> {q[5]}</label><hr>
"""

    return page(f"""
<div class="timer">Time Left: <span id="t">{timer}</span>s</div>
<form method="post" action="/submit">
{qhtml}
<button class="btn btn-success w-100">Submit Quiz</button>
</form>
<script>
let t = {timer};
setInterval(function(){{
  document.getElementById("t").innerHTML = t;
  if(t <= 0) document.forms[0].submit();
  t--;
}},1000);
</script>
""")

@app.route("/submit", methods=["POST"])
def submit():
    pid = session["pid"]
    score = 0
    for qid, ans in request.form.items():
        c = cur.execute("SELECT correct FROM questions WHERE id=?", (qid,)).fetchone()[0]
        if ans == c:
            score += 1

    cur.execute(
        "UPDATE participants SET score=?, end=? WHERE id=?",
        (score, time.time(), pid)
    )
    con.commit()
    return page("<h3 class='text-center'>✅ Successfully Submitted</h3>")

# ---------------- ADMIN ----------------
@app.route("/admin", methods=["GET","POST"])
def admin():
    if request.method == "POST" and "login" in request.form:
        if request.form["u"] == "1234" and request.form["p"] == "pass@123":
            session["admin"] = True
        else:
            return page("<h4>Invalid Login</h4>")

    if "admin" not in session:
        return page("""
<form method="post">
<input class="form-control mb-2" name="u" placeholder="Username">
<input class="form-control mb-2" type="password" name="p" placeholder="Password">
<button name="login" class="btn btn-dark w-100">Login</button>
</form>
""")

    rows = cur.execute(
        "SELECT name,score,(end-start) FROM participants ORDER BY score DESC,(end-start)"
    ).fetchall()

    table = ""
    for i, r in enumerate(rows):
        table += f"<tr><td>{i+1}</td><td>{r[0]}</td><td>{r[1]}</td><td>{round(r[2],1)}</td></tr>"

    return page(f"""
<a href="/addq" class="btn btn-primary mb-2">Add Question</a>
<a href="/timer" class="btn btn-warning mb-2 ms-2">Set Timer</a>
<a href="/export" class="btn btn-success mb-2 ms-2">Excel</a>

<table class="table table-bordered mt-3">
<tr><th>Rank</th><th>Name</th><th>Score</th><th>Time</th></tr>
{table}
</table>
""")

@app.route("/addq", methods=["GET","POST"])
def addq():
    if "admin" not in session:
        return redirect("/admin")

    if request.method == "POST":
        cur.execute(
            "INSERT INTO questions(q,a,b,c,d,correct) VALUES(?,?,?,?,?,?)",
            (request.form["q"], request.form["a"], request.form["b"],
             request.form["c"], request.form["d"], request.form["correct"])
        )
        con.commit()
        return redirect("/admin")

    return page("""
<form method="post">
<input class="form-control mb-2" name="q" placeholder="Question">
<input class="form-control mb-2" name="a" placeholder="Option A">
<input class="form-control mb-2" name="b" placeholder="Option B">
<input class="form-control mb-2" name="c" placeholder="Option C">
<input class="form-control mb-2" name="d" placeholder="Option D">
<input class="form-control mb-2" name="correct" placeholder="Correct (a/b/c/d)">
<button class="btn btn-success w-100">Add Question</button>
</form>
""")

@app.route("/timer", methods=["GET","POST"])
def timer():
    if "admin" not in session:
        return redirect("/admin")

    if request.method == "POST":
        cur.execute("UPDATE settings SET timer=? WHERE id=1", (request.form["t"],))
        con.commit()
        return redirect("/admin")

    return page("""
<form method="post">
<input class="form-control mb-2" name="t" placeholder="Time in seconds">
<button class="btn btn-warning w-100">Set Timer</button>
</form>
""")

@app.route("/export")
def export():
    wb = Workbook()
    ws = wb.active
    ws.merge_cells("A1:F1")
    ws["A1"] = "TECHNOSPECTRUM 2K26 – QUIZ RESULTS"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A1"].alignment = Alignment(horizontal="center")
    ws.append(["Rank","Name","Email","Contact","Score","Time"])

    rows = cur.execute(
        "SELECT name,email,contact,score,(end-start) FROM participants ORDER BY score DESC,(end-start)"
    ).fetchall()

    for i, r in enumerate(rows):
        ws.append([i+1, r[0], r[1], r[2], r[3], round(r[4],1)])

    wb.save("Technospectrum_2K26.xlsx")
    return send_file("Technospectrum_2K26.xlsx", as_attachment=True)

app.run(host="0.0.0.0", port=5000)