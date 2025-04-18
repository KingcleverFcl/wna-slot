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
    __tablename__ = "casino_users"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(64), unique=True, nullable=False)
    balance = db.Column(db.Integer, default=0)

class CasinoCode(db.Model):
    __tablename__ = "casino_codes"
    code = db.Column(db.String(64), primary_key=True)
    amount = db.Column(db.Integer, nullable=False)
    total_activation = db.Column(db.Integer, nullable=False)

### ШАБЛОНЫ ###

login_html = """
<!doctype html>
<html>
<head>
    <title>Enter Code</title>
    <style>
        body { background: #111; color: #eee; font-family: monospace; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; }
        input, button { padding: 10px; font-size: 18px; }
        input { width: 400px; }
        ul { color: red; margin-top: 10px; }
    </style>
</head>
<body>
    <h2>Enter your 64-character code</h2>
    <form method="post">
        <input name="code" maxlength=64>
        <button type="submit">Enter</button>
    </form>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <ul>{% for m in messages %}<li>{{ m }}</li>{% endfor %}</ul>
      {% endif %}
    {% endwith %}
</body>
</html>
"""

game_html = """
<!doctype html>
<html>
<head>
    <title>WNA CASINO</title>
    <style>
        body { background: url('/static/main.png') no-repeat center center fixed; background-size: cover; font-family: monospace; color: #fff; text-align: center; }
        .balance { margin: 20px; font-size: 24px; }
        .balance a { color: #fff; text-decoration: none; padding: 5px 10px; background: #444; border-radius: 5px; margin-left: 10px; }
        .grid { font-size: 26px; margin-top: 20px; white-space: pre; }
        .controls { margin-top: 20px; }
        .controls button, input { margin: 5px; padding: 10px 20px; font-size: 18px; background: #555; color: #fff; border: none; border-radius: 8px; }
        .controls button:hover { background: #777; cursor: pointer; }
        .popup { display: {{ 'block' if show_popup else 'none' }}; position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: #222; padding: 20px; border: 2px solid #fff; }
    </style>
</head>
<body>
    <div class="balance">
        Balance: {{ balance }}
        <a href="?topup=1">+</a>
        <a href="/logout">Logout</a>
    </div>

    {% if show_popup %}
    <div class="popup">
        <form method="post">
            <p>Enter top-up code:</p>
            <input name="topup_code" maxlength=64>
            <button type="submit">Submit</button>
        </form>
    </div>
    {% endif %}

    <form method="post" class="controls">
        <input name="bet" type="number" value="{{ bet }}" min="1" placeholder="Bet">
        <button name="spin" value="1">СПИН</button>
        <button name="toggle_auto" value="1">{{ 'Выкл' if auto else 'Вкл' }}</button>
        {% if auto %}
            <button name="auto_spin" value="1">Авто-спин ({{ auto_left }})</button>
        {% endif %}
    </form>

    {% if grid %}
    <div class="grid">
        {% for row in grid %}{{ row }}\n{% endfor %}
    </div>
    <p>{{ result }}</p>
    {% endif %}

    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <ul style="color: red;">{% for m in messages %}<li>{{ m }}</li>{% endfor %}</ul>
      {% endif %}
    {% endwith %}
</body>
</html>
"""

### РОУТЫ ###

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

@app.route("/game", methods=["GET", "POST"])
def game():
    player = get_player()
    if not player:
        return redirect("/")

    grid, result = None, ""
    bet = int(request.form.get("bet", session.get("bet", 10)))
    session["bet"] = bet

    # Обработка пополнения
    if "topup" in request.args:
        return render_template_string(game_html, balance=player.balance, grid=None, result="", show_popup=True, auto=session.get("auto", False), auto_left=session.get("auto_left", 0), bet=bet)

    if request.method == "POST":
        if "topup_code" in request.form:
            code = request.form["topup_code"].strip()
            topup = CasinoCode.query.filter_by(code=code).first()
            if topup and topup.total_activation > 0:
                player.balance += topup.amount
                topup.total_activation -= 1
                db.session.commit()
                flash(f"Added {topup.amount} coins!")
            else:
                flash("Invalid or expired code.")
        elif "toggle_auto" in request.form:
            session["auto"] = not session.get("auto", False)
        elif "auto_spin" in request.form and session.get("auto", False):
            spins_left = session.get("auto_left", 10)
            if player.balance >= bet:
                player.balance -= bet
                grid = [[random.randint(1, 9) for _ in range(5)] for _ in range(3)]
                reward = check_win(grid)
                player.balance += reward
                result = f"Auto-Spin: Won {reward} coins!" if reward > 0 else "No win."
                spins_left -= 1
                session["auto_left"] = spins_left
                if spins_left <= 0:
                    session["auto"] = False
                db.session.commit()
            else:
                flash("Not enough balance for auto-spin.")
        elif "spin" in request.form:
            if player.balance < bet:
                flash("Not enough balance.")
            else:
                player.balance -= bet
                grid = [[random.randint(1, 9) for _ in range(5)] for _ in range(3)]
                reward = check_win(grid)
                player.balance += reward
                result = f"You won {reward} coins!" if reward > 0 else "No win this time."
                db.session.commit()

    return render_template_string(game_html, balance=player.balance, grid=grid, result=result, show_popup=False, auto=session.get("auto", False), auto_left=session.get("auto_left", 10), bet=bet)

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
