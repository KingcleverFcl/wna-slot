import os
import random
from flask import Flask, request, redirect, session, flash, render_template_string
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///local.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

### МОДЕЛИ ###
class CasinoUser(db.Model):
    __tablename__ = "casino_users"  # ✅ исправлено имя таблицы
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False)
    balance = db.Column(db.Integer, default=0)

class CasinoCode(db.Model):
    __tablename__ = "casino_codes"  # ✅ исправлено имя таблицы
    code = db.Column(db.String(64), primary_key=True)
    amount = db.Column(db.Integer, nullable=False)
    total_activation = db.Column(db.Integer, nullable=False)

### HTML ###
login_html = """
<!doctype html><title>Login</title>
<h2>Enter your 64-character code</h2>
<form method=post>
  <input name=code style="width:400px;" maxlength=64>
  <button type=submit>Enter</button>
</form>
{% with messages = get_flashed_messages() %}
  {% if messages %}<ul>{% for m in messages %}<li>{{ m }}</li>{% endfor %}</ul>{% endif %}
{% endwith %}
"""

game_html = """
<!doctype html><title>Slot Machine</title>
<h2>Balance: {{ balance }} | <a href='/logout'>Logout</a></h2>
<form method=post>
  <button type=submit name=spin value=1>SPIN (10 coins)</button>
</form>
{% if grid %}
<pre style="font-size: 22px;">{% for row in grid %}{{ row }}\n{% endfor %}</pre>
<p>{{ result }}</p>
{% endif %}
"""

### ЛОГИН ###
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        if len(code) != 64:
            flash("Invalid code length.")
            return render_template_string(login_html)

        player = CasinoUser.query.filter_by(code=code).first()
        if player:
            session["uid"] = player.id
            return redirect("/game")

        code_data = CasinoCode.query.filter_by(code=code).first()
        if not code_data or code_data.total_activation <= 0:
            flash("Code not found or all activations used.")
            return render_template_string(login_html)

        new_player = CasinoUser(code=code, balance=code_data.amount)
        code_data.total_activation -= 1
        db.session.add(new_player)
        db.session.commit()
        session["uid"] = new_player.id
        return redirect("/game")

    return render_template_string(login_html)

### ИГРА ###
@app.route("/game", methods=["GET", "POST"])
def game():
    player = get_player()
    if not player:
        return redirect("/")

    grid = None
    result = ""
    if request.method == "POST":
        if player.balance < 10:
            flash("Not enough balance.")
        else:
            player.balance -= 10
            grid = [[random.randint(1, 9) for _ in range(5)] for _ in range(3)]
            reward = check_win(grid)
            player.balance += reward
            result = f"You won {reward} coins!" if reward > 0 else "No win this time."
            db.session.commit()

    return render_template_string(game_html, balance=player.balance, grid=grid, result=result)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

def get_player():
    uid = session.get("uid")
    return CasinoUser.query.get(uid) if uid else None

def check_win(grid):
    reward = 0
    for row in grid:
        if all(x == row[0] for x in row):
            reward += 100
    flat = [n for row in grid for n in row]
    if all(x == flat[0] for x in flat):
        reward += 1000
    return reward

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
