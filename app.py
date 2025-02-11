from flask import Flask, render_template, redirect, request, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secretkey"

Toll_fee = 100

def get_db_connection():
    conn = sqlite3.connect("toll.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS USER_INFO(
            NAME TEXT NOT NULL,
            CAR_NO TEXT PRIMARY KEY,
            EMAIL TEXT UNIQUE NOT NULL,
            PASSWORD TEXT NOT NULL,
            BALANCE REAL DEFAULT 0.0
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS TRANSACTIONS(
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            DATE TEXT NOT NULL,
            CAR_NO TEXT NOT NULL,
            INTIME TEXT NOT NULL,
            CARAMOUNT REAL NOT NULL,
            FOREIGN KEY(CAR_NO) REFERENCES USER_INFO(CAR_NO) ON DELETE CASCADE          
        );
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/deduct_money", methods=["POST"])
def deduct_money():
    car_no = request.form["car_no"]

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch user balance
    cursor.execute("SELECT BALANCE FROM USER_INFO WHERE CAR_NO = ?", (car_no,))
    user = cursor.fetchone()

    if user:
        balance = user["BALANCE"]
        if balance >= Toll_fee:
            # Deduct toll fee
            new_balance = balance - Toll_fee
            cursor.execute("UPDATE USER_INFO SET BALANCE = ? WHERE CAR_NO = ?", (new_balance, car_no))

            # Insert transaction record
            date_now = datetime.now().strftime("%Y-%m-%d")  # Get current date
            time_now = datetime.now().strftime("%H:%M:%S")  # Get current time
            cursor.execute(
                "INSERT INTO TRANSACTIONS (DATE, CAR_NO, INTIME, CARAMOUNT) VALUES (?, ?, ?, ?)", 
                (date_now, car_no, time_now, Toll_fee)
            )

            conn.commit()
            conn.close()
            return f"Toll fee deducted successfully! New Balance: ${new_balance:.2f} <br><a href='/'>Back</a>"
        else:
            conn.close()
            return "Required fee not available. <a href='/'>Back</a>"
    else:
        return "Car number not found. <a href='/'>Back</a>"

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT NAME FROM USER_INFO WHERE EMAIL = ? AND PASSWORD = ?", (email, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            username = user["NAME"].replace(" ", "_")
            session["email"] = email
            session["username"] = username
            return redirect(f"/{username}")
        else:
            return "Invalid credentials. <a href='/login'>Try again</a>"

    return render_template("login.html")  # Show login page for GET requests


@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # Hardcoded admin credentials (you can store these in the database instead)
        ADMIN_EMAIL = "admin@toll.com"
        ADMIN_PASSWORD = "admin123"

        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session["admin"] = True  # Store admin login status in session
            return redirect("/admin_dashboard")
        else:
            return "Invalid admin credentials. <a href='/admin'>Try again</a>"

    return render_template("admin_login.html")


@app.route("/admin_dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect("/admin")  # Redirect to admin login if not logged in

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM TRANSACTIONS ORDER BY DATE DESC")
    transactions = cursor.fetchall()
    conn.close()

    return render_template("admin_dashboard.html", transactions=transactions)

@app.route("/admin_logout", methods=["POST"])
def admin_logout():
    session.pop("admin", None)
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        car_no = request.form["car_no"]
        email = request.form["email"]
        password = request.form["password"]

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO USER_INFO (NAME, CAR_NO, EMAIL, PASSWORD, BALANCE) VALUES (?, ?, ?, ?, ?)", 
                           (name, car_no, email, password, 0.0))
            conn.commit()
            conn.close()
            return redirect("/")  # Redirect to login page
        except sqlite3.IntegrityError:
            return "Email or Car Number already exists. <a href='/register'>Try again</a>"
    
    return render_template("register.html")

@app.route("/add_money", methods=["POST"])
def add_money():
    if "email" not in session:
        return redirect("/")
    
    amount = float(request.form["amount"])
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE USER_INFO SET BALANCE = BALANCE + ? WHERE EMAIL = ?", (amount, session["email"]))
    conn.commit()
    conn.close()
    return redirect(f"/{session['username']}")

@app.route("/<username>")
def user_page(username):
    if "email" not in session or session["username"] != username:
        return redirect("/")  

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT NAME, CAR_NO, BALANCE FROM USER_INFO WHERE NAME = ?", (username.replace("_", " "),))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return "User not found"

    return render_template("user.html", user=user)

@app.route("/logout", methods=["POST"])
def logout():
    session.pop("email", None)
    session.pop("username", None)
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)