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
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>Слот-машина</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      background: #000;
      color: #fff;
      margin: 0;
      padding: 0;
    }

    .container {
      max-width: 800px;
      margin: 0 auto;
      padding: 20px;
      text-align: center;
    }

    .top-bar {
      display: flex;
      justify-content: space-between;
      margin-bottom: 10px;
      align-items: center;
    }

    .top-left, .top-right {
      display: flex;
      gap: 10px;
      align-items: center;
    }

    .balance-code {
      position: relative;
    }

    #codeInputContainer {
      position: absolute;
      top: 25px;
      right: 0;
      display: none;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(5, 60px);
      grid-template-rows: repeat(3, 60px);
      gap: 10px;
      justify-content: center;
      margin: 30px 0;
    }

    .cell {
      width: 60px;
      height: 60px;
      background: #111;
      border: 2px solid #555;
      font-size: 28px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .bottom-controls {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0 10px;
      margin-bottom: 20px;
    }

    .bet-input {
      width: 100px;
      padding: 5px;
      text-align: center;
    }

    .spin-button {
      padding: 10px 30px;
      font-size: 18px;
      cursor: pointer;
      background: #28a745;
      border: none;
      color: white;
      margin-top: 20px;
    }

    .spin-button:disabled {
      background: #666;
      cursor: not-allowed;
    }
  </style>
</head>
<body>

<div class="container">
  <div class="top-bar">
    <div class="top-left">
      <label>Авто-спин:</label>
      <select id="autospin">
        <option value="off">Выкл</option>
        <option value="on">Вкл</option>
      </select>
      <label>Кол-во:</label>
      <input type="number" id="autospinCount" min="0" value="0" style="width: 50px;">
    </div>

    <div class="top-right">
      <div>Баланс: <span id="balance">100</span></div>
      <div class="balance-code">
        <button onclick="toggleCodeInput()">+</button>
        <div id="codeInputContainer">
          <input type="text" id="codeInput" placeholder="Введите код">
          <button onclick="applyCode()">ОК</button>
        </div>
      </div>
    </div>
  </div>

  <div class="grid" id="slotGrid">
    <!-- 15 ячеек 3x5 -->
    <div class="cell">0</div><div class="cell">0</div><div class="cell">0</div><div class="cell">0</div><div class="cell">0</div>
    <div class="cell">0</div><div class="cell">0</div><div class="cell">0</div><div class="cell">0</div><div class="cell">0</div>
    <div class="cell">0</div><div class="cell">0</div><div class="cell">0</div><div class="cell">0</div><div class="cell">0</div>
  </div>

  <div class="bottom-controls">
    <div>
      <label>Ставка:</label>
      <input type="number" id="bet" class="bet-input" min="10" max="1000" value="10">
    </div>
    <div>
      <label>Пропуск анимации:</label>
      <select id="skipAnimation">
        <option value="off">Выкл</option>
        <option value="on">Вкл</option>
      </select>
    </div>
  </div>

  <button class="spin-button" id="spinButton" onclick="startSpin()">СПИН</button>
</div>

<script>
  let balance = 100;
  let autoSpinning = false;

  const cells = Array.from(document.querySelectorAll(".cell"));

  function toggleCodeInput() {
    const input = document.getElementById("codeInputContainer");
    input.style.display = input.style.display === "block" ? "none" : "block";
  }

  function applyCode() {
    const code = document.getElementById("codeInput").value.trim();
    // Тут будет запрос к серверу для проверки кода и пополнения баланса
    if (code === "DEMO123") {
      balance += 100;
      updateBalance();
      alert("Баланс пополнен!");
    } else {
      alert("Неверный код");
    }
    document.getElementById("codeInput").value = "";
    document.getElementById("codeInputContainer").style.display = "none";
  }

  function updateBalance() {
    document.getElementById("balance").textContent = balance;
  }

  function startSpin() {
    const bet = parseInt(document.getElementById("bet").value);
    const skip = document.getElementById("skipAnimation").value === "on";
    const autoSpin = document.getElementById("autospin").value === "on";
    let autoCount = parseInt(document.getElementById("autospinCount").value);

    if (autoSpinning && autoCount > 0) {
      alert("Авто-спин активен, подождите");
      return;
    }

    if (bet > balance) {
      alert("Недостаточно средств!");
      return;
    }

    balance -= bet;
    updateBalance();

    if (autoSpin && autoCount > 0) {
      autoSpinning = true;
      document.getElementById("spinButton").disabled = true;
    }

    const doSpin = (col = 0) => {
      if (skip) {
        for (let i = 0; i < 15; i++) {
          cells[i].textContent = Math.floor(Math.random() * 9) + 1;
        }
        afterSpin();
        return;
      }

      if (col >= 5) {
        afterSpin();
        return;
      }

      let colIndices = [col, col + 5, col + 10];
      let interval = setInterval(() => {
        colIndices.forEach(i => {
          cells[i].textContent = Math.floor(Math.random() * 9) + 1;
        });
      }, 100);

      setTimeout(() => {
        clearInterval(interval);
        colIndices.forEach(i => {
          cells[i].textContent = Math.floor(Math.random() * 9) + 1;
        });
        doSpin(col + 1);
      }, 800);
    };

    doSpin();
  }

  function afterSpin() {
    let autoCount = parseInt(document.getElementById("autospinCount").value);
    if (document.getElementById("autospin").value === "on" && autoCount > 0) {
      autoCount--;
      document.getElementById("autospinCount").value = autoCount;
      if (autoCount > 0) {
        setTimeout(startSpin, 1500);
      } else {
        autoSpinning = false;
        document.getElementById("spinButton").disabled = false;
      }
    } else {
      autoSpinning = false;
      document.getElementById("spinButton").disabled = false;
    }
  }
</script>

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
