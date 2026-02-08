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
email TEXT,
contact TEXT,
score INTEGER DEFAULT 0,
start REAL,
end REAL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS questions(
id INTEGER PRIMARY KEY AUTOINCREMENT,
q TEXT,
a TEXT,b TEXT,c TEXT,d TEXT,
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
    cur.execute("INSERT INTO settings VALUES(1,300)")
    con.commit()

# ---------------- UI ----------------
def page(body, admin=False):
    nav = ""
    if admin:
        nav = '<div class="text-end mb-2"><a href="/admin" class="btn btn-sm btn-dark">Admin Home</a></div>'

    return f"""
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{{background:linear-gradient(135deg,#667eea,#764ba2);}}
.card{{border-radius:18px}}
h2{{color:white}}
</style>
</head>
<body>
<div class="container mt-4">
{nav}
<h2 class="text-center">TECHNOSPECTRUM 2K26</h2>
<div class="card p-4 shadow mt-3">{body}</div>
</div>
</body>
</html>
"""

def admin_required():
    return session.get("admin")

# ---------------- USER FLOW ----------------
@app.route("/", methods=["GET","POST"])
def register():
    if request.method == "POST":
        session["tmp"] = request.form
        return redirect("/otp")

    return page("""
<form method="post">
<input class="form-control mb-2" name="name" placeholder="Full Name" required>
<input class="form-control mb-2" name="email" placeholder="Email" required>
<input class="form-control mb-2" name="contact" placeholder="Contact" required>
<button class="btn btn-primary w-100">Continue</button>
</form>
""")

@app.route("/otp", methods=["GET","POST"])
def otp():
    if request.method == "POST":
        if request.form.get("otp") == "1211":
            d = session.get("tmp")
            if not d:
                return redirect("/")
            cur.execute(
                "INSERT INTO participants(name,email,contact,start) VALUES(?,?,?,?)",
                (d["name"], d["email"], d["contact"], time.time())
            )
            con.commit()
            session["pid"] = cur.lastrowid
            return redirect("/quiz")
        return page("<h4 class='text-danger text-center'>Wrong OTP</h4>")

    return page("""
<form method="post">
<input class="form-control mb-2" name="otp" placeholder="Enter OTP" required>
<button class="btn btn-success w-100">Verify</button>
</form>
""")

@app.route("/quiz")
def quiz():
    if "pid" not in session:
        return redirect("/")

    qs = cur.execute("SELECT * FROM questions").fetchall()
    if len(qs) == 0:
        return page("""
        <h4 class="text-center text-danger">
        Quiz not available yet.<br>Please wait for coordinator.
        </h4>
        """)

    random.shuffle(qs)
    timer = cur.execute("SELECT timer FROM settings").fetchone()[0]

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
<div class="alert alert-info text-center">
Time Left: <span id="t">{timer}</span> sec
</div>
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
    if "pid" not in session:
        return redirect("/")

    score = 0
    for q, a in request.form.items():
        ans = cur.execute("SELECT correct FROM questions WHERE id=?", (q,)).fetchone()
        if ans and a == ans[0]:
            score += 1

    cur.execute(
        "UPDATE participants SET score=?, end=? WHERE id=?",
        (score, time.time(), session["pid"])
    )
    con.commit()
    session.clear()

    return page("<h3 class='text-success text-center'>You have successfully submitted the quiz</h3>")

# ---------------- ADMIN ----------------
@app.route("/admin", methods=["GET","POST"])
def admin():
    if request.method == "POST":
        if request.form.get("u") == "1234" and request.form.get("p") == "pass@123":
            session["admin"] = 1

    if not admin_required():
        return page("""
<form method="post">
<input class="form-control mb-2" name="u" placeholder="Username">
<input class="form-control mb-2" type="password" name="p" placeholder="Password">
<button class="btn btn-dark w-100">Login</button>
</form>
""")

    return page("""
<a href="/addq" class="btn btn-primary w-100 mb-2">Add Question</a>
<a href="/settimer" class="btn btn-info w-100 mb-2">Set Timer</a>
<a href="/leaderboard" class="btn btn-secondary w-100 mb-2">Leaderboard</a>
<a href="/graph" class="btn btn-dark w-100 mb-2">Graph Analytics</a>
<a href="/export" class="btn btn-success w-100 mb-2">Download Excel</a>
<a href="/clear" class="btn btn-danger w-100 mb-2">Clear Leaderboard</a>
""", admin=True)

@app.route("/addq", methods=["GET","POST"])
def addq():
    if not admin_required():
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
<input class="form-control mb-2" name="q" placeholder="Question" required>
<input class="form-control mb-2" name="a" placeholder="Option A" required>
<input class="form-control mb-2" name="b" placeholder="Option B" required>
<input class="form-control mb-2" name="c" placeholder="Option C" required>
<input class="form-control mb-2" name="d" placeholder="Option D" required>
<select class="form-control mb-2" name="correct">
<option value="a">A</option>
<option value="b">B</option>
<option value="c">C</option>
<option value="d">D</option>
</select>
<button class="btn btn-success w-100">Add Question</button>
</form>
""", admin=True)

@app.route("/leaderboard")
def leaderboard():
    if not admin_required():
        return redirect("/admin")

    rows = cur.execute(
        "SELECT name,score,(end-start) FROM participants ORDER BY score DESC"
    ).fetchall()

    t=""
    for i,r in enumerate(rows):
        t += f"<tr><td>{i+1}</td><td>{r[0]}</td><td>{r[1]}</td><td>{round(r[2],1)} s</td></tr>"

    return page(f"""
<table class="table table-striped">
<tr><th>Rank</th><th>Name</th><th>Score</th><th>Time Taken</th></tr>
{t}
</table>
""", admin=True)

@app.route("/graph")
def graph():
    if not admin_required():
        return redirect("/admin")

    rows = cur.execute("SELECT name,score FROM participants").fetchall()
    names = [r[0] for r in rows]
    scores = [r[1] for r in rows]

    return page(f"""
<canvas id="c"></canvas>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
new Chart(document.getElementById("c"), {{
type:"bar",
data:{{labels:{names},datasets:[{{data:{scores},backgroundColor:"#6f42c1"}}]}}
}});
</script>
""", admin=True)

@app.route("/export")
def export():
    if not admin_required():
        return redirect("/admin")

    wb = Workbook()
    ws = wb.active
    ws.append(["Rank","Name","Email","Contact","Score","Time (sec)"])
    for c in ws[1]:
        c.font = Font(bold=True)
        c.alignment = Alignment(horizontal="center")

    rows = cur.execute(
        "SELECT name,email,contact,score,(end-start) FROM participants ORDER BY score DESC"
    ).fetchall()

    for i,r in enumerate(rows):
        ws.append([i+1,r[0],r[1],r[2],r[3],round(r[4],1)])

    wb.save("Technospectrum_2K26.xlsx")
    return send_file("Technospectrum_2K26.xlsx", as_attachment=True)

@app.route("/settimer", methods=["GET","POST"])
def settimer():
    if not admin_required():
        return redirect("/admin")

    if request.method == "POST":
        total = int(request.form["m"])*60 + int(request.form["s"])
        cur.execute("UPDATE settings SET timer=?", (total,))
        con.commit()
        return redirect("/admin")

    return page("""
<form method="post">
<input class="form-control mb-2" name="m" placeholder="Minutes" required>
<input class="form-control mb-2" name="s" placeholder="Seconds" required>
<button class="btn btn-info w-100">Set Timer</button>
</form>
""", admin=True)

@app.route("/clear")
def clear():
    if not admin_required():
        return redirect("/admin")
    cur.execute("DELETE FROM participants")
    con.commit()
    return redirect("/admin")

app.run(host="0.0.0.0", port=5000)
