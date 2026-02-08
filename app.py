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

cur.execute("""CREATE TABLE IF NOT EXISTS participants(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
email TEXT,
contact TEXT,
score INTEGER,
start REAL,
end REAL
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS questions(
id INTEGER PRIMARY KEY AUTOINCREMENT,
q TEXT,a TEXT,b TEXT,c TEXT,d TEXT,correct TEXT
)""")

cur.execute("""CREATE TABLE IF NOT EXISTS settings(
id INTEGER PRIMARY KEY,
timer INTEGER,
quiz_open INTEGER
)""")

if cur.execute("SELECT COUNT(*) FROM settings").fetchone()[0] == 0:
    cur.execute("INSERT INTO settings VALUES(1,300,1)")
    con.commit()

# ---------------- UI ----------------
def page(body, admin=False):
    menu = ""
    if admin:
        menu = """
<div style="text-align:right">
<a href="/admin" class="btn btn-sm btn-dark">Admin</a>
</div>
"""
    return f"""
<!doctype html>
<html>
<head>
<meta name=viewport content="width=device-width,initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel=stylesheet>
<style>
body{{background:linear-gradient(135deg,#667eea,#764ba2);}}
.card{{border-radius:18px}}
h2{{color:white}}
</style>
</head>
<body>
<div class=container mt-4>
{menu}
<h2 class=text-center>TECHNOSPECTRUM 2K26</h2>
<div class="card p-4 shadow mt-3">{body}</div>
</div>
</body>
</html>
"""

def admin_required():
    return session.get("admin")

# ---------------- USER ----------------
@app.route("/", methods=["GET","POST"])
def register():
    if request.method == "POST":
        session["tmp"] = request.form
        return redirect("/otp")

    return page("""
<form method=post>
<input class=form-control mb-2 name=name placeholder="Name" required>
<input class=form-control mb-2 name=email placeholder="Email" required>
<input class=form-control mb-2 name=contact placeholder="Contact" required>
<button class="btn btn-primary w-100">Continue</button>
</form>
""")

@app.route("/otp", methods=["GET","POST"])
def otp():
    if request.method == "POST":
        if request.form["otp"] == "1211":
            d = session["tmp"]
            cur.execute(
                "INSERT INTO participants(name,email,contact,start) VALUES(?,?,?,?)",
                (d["name"], d["email"], d["contact"], time.time())
            )
            con.commit()
            session["pid"] = cur.lastrowid
            return redirect("/quiz")
        return page("<h4 class=text-danger>Wrong OTP</h4>")

    return page("""
<form method=post>
<input class=form-control mb-2 name=otp placeholder="Enter OTP">
<button class="btn btn-success w-100">Verify</button>
</form>
""")

@app.route("/quiz")
def quiz():
    qs = cur.execute("SELECT * FROM questions").fetchall()
    random.shuffle(qs)
    timer = cur.execute("SELECT timer FROM settings").fetchone()[0]

    qhtml = ""
    for q in qs:
        qhtml += f"""
<b>{q[1]}</b><br>
<label><input type=radio name={q[0]} value=a> {q[2]}</label><br>
<label><input type=radio name={q[0]} value=b> {q[3]}</label><br>
<label><input type=radio name={q[0]} value=c> {q[4]}</label><br>
<label><input type=radio name={q[0]} value=d> {q[5]}</label><hr>
"""

    return page(f"""
<div class="alert alert-info text-center">Time Left: <span id=t>{timer}</span></div>
<form method=post action=/submit>
{qhtml}
<button class="btn btn-success w-100">Submit</button>
</form>
<script>
let t={timer};
setInterval(function(){{
document.getElementById("t").innerHTML=t;
if(t<=0)document.forms[0].submit();
t--;
}},1000);
</script>
""")

@app.route("/submit", methods=["POST"])
def submit():
    score = 0
    for q, a in request.form.items():
        if a == cur.execute("SELECT correct FROM questions WHERE id=?", (q,)).fetchone()[0]:
            score += 1

    cur.execute(
        "UPDATE participants SET score=?, end=? WHERE id=?",
        (score, time.time(), session["pid"])
    )
    con.commit()

    return page("<h3 class=text-success text-center>Successfully Submitted</h3>")

# ---------------- ADMIN ----------------
@app.route("/admin", methods=["GET","POST"])
def admin():
    if request.method == "POST":
        if request.form["u"] == "1234" and request.form["p"] == "pass@123":
            session["admin"] = 1

    if not admin_required():
        return page("""
<form method=post>
<input class=form-control mb-2 name=u placeholder=Username>
<input class=form-control mb-2 type=password name=p placeholder=Password>
<button class="btn btn-dark w-100">Login</button>
</form>
""")

    return page("""
<a href=/leaderboard class="btn btn-secondary w-100 mb-2">Leaderboard</a>
<a href=/addq class="btn btn-primary w-100 mb-2">Add Question</a>
<a href=/export class="btn btn-success w-100 mb-2">Download Excel</a>
<a href=/clear class="btn btn-danger w-100 mb-2">Clear Leaderboard</a>
""", admin=True)

@app.route("/leaderboard")
def leaderboard():
    rows = cur.execute(
        "SELECT id,name,score,(end-start) FROM participants ORDER BY score DESC"
    ).fetchall()

    t = ""
    for i, r in enumerate(rows):
        t += f"<tr><td>{i+1}</td><td><a href=/user/{r[0]}>{r[1]}</a></td><td>{r[2]}</td><td>{round(r[3],1)} s</td></tr>"

    return page(f"""
<table class=table>
<tr><th>Rank</th><th>Name</th><th>Score</th><th>Time Taken</th></tr>
{t}
</table>
""", admin=True)

@app.route("/user/<int:uid>")
def user_detail(uid):
    r = cur.execute(
        "SELECT name,score,(end-start) FROM participants WHERE id=?", (uid,)
    ).fetchone()

    return page(f"""
<h4>{r[0]}</h4>
<p>Score: {r[1]}</p>
<p>Total Time Taken: {round(r[2],1)} seconds</p>
""", admin=True)

@app.route("/clear")
def clear():
    cur.execute("DELETE FROM participants")
    con.commit()
    return redirect("/admin")

@app.route("/export")
def export():
    wb = Workbook()
    ws = wb.active

    ws.append(["Rank","Name","Email","Contact","Score","Time Taken (s)"])
    for c in ws[1]:
        c.font = Font(bold=True)

    rows = cur.execute(
        "SELECT name,email,contact,score,(end-start) FROM participants ORDER BY score DESC"
    ).fetchall()

    for i, r in enumerate(rows):
        ws.append([i+1, r[0], r[1], r[2], r[3], round(r[4],1)])

    wb.save("Technospectrum_2K26.xlsx")
    return send_file("Technospectrum_2K26.xlsx", as_attachment=True)

app.run(host="0.0.0.0", port=5000)
