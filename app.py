from flask import Flask, render_template, request
import pdfplumber
import os
import re
import sqlite3
import csv
from flask import Response
app = Flask(__name__)
conn = sqlite3.connect("resume.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS resumes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    phone TEXT,
    skills TEXT
)
""")

conn.commit()

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def extract_text(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text
def extract_email(text):
    text = text.replace("gma\nil.com", "gmail.com")
    text = text.replace("\n", " ")

    pattern = r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
    match = re.search(pattern, text)

    if match:
        return match.group(0)

    return "Not Found"
def extract_phone(text):
    phone = re.findall(r'\b\d{10}\b', text)
    return phone[0] if phone else "Not Found"

def extract_name(text):
    lines = text.split("\n")
    return lines[0] if lines else "Not Found"
def extract_skills(text):
    skills_database = [
        "Python",
        "AutoCAD",
        "STAAD.Pro",
        "MIDAS Civil",
        "Revit",
        "ETABS",
        "SAP2000",
        "Tekla",
        "MS Excel",
        "Structural Analysis",
        "Surveying",
        "Communication Skills",
        "Teamwork",
        "Problem Solving",
        "Time Management",
        "Adaptability"
    ]

    found = []

    for skill in skills_database:
        if skill.lower() in text.lower():
            found.append(skill)

    return found
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        file = request.files["resume"]

        if file:
            path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
            file.save(path)

            text = extract_text(path)
            print(text)
            name = extract_name(text)
            email = extract_email(text)
            phone = extract_phone(text)
            skills = extract_skills(text)

            cursor.execute("SELECT * FROM resumes WHERE email=?", (email,))
            existing = cursor.fetchone()

        if not existing:
            cursor.execute(
            "INSERT INTO resumes(name,email,phone,skills) VALUES(?,?,?,?)",
             (name, email, phone, ", ".join(skills))
                )
            conn.commit()

            return render_template("result.html", text=text,name=name,email=email,phone=phone,skills=skills)

    return render_template("index.html")

@app.route("/candidates")
def candidates():
    cursor.execute("SELECT * FROM resumes")
    data = cursor.fetchall()

    return render_template("candidates.html", data=data)
@app.route("/search", methods=["GET", "POST"])
def search():

    results = []

    if request.method == "POST":
        skill = request.form["skill"]

        cursor.execute(
            "SELECT * FROM resumes WHERE skills LIKE ?",
            ('%' + skill + '%',)
        )

        results = cursor.fetchall()

    return render_template("search.html", results=results)

@app.route("/delete/<int:id>")
def delete(id):

    cursor.execute("DELETE FROM resumes WHERE id=?", (id,))
    conn.commit()

    return "Candidate Deleted Successfully! <br><br> <a href='/candidates'>Back</a>"

@app.route("/export")
def export():

    cursor.execute("SELECT * FROM resumes")
    data = cursor.fetchall()

    def generate():
        yield "ID,Name,Email,Phone,Skills\n"

        for row in data:
            yield f"{row[0]},{row[1]},{row[2]},{row[3]},\"{row[4]}\"\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            "attachment;filename=resumes.csv"
        }
    )
if __name__ == "__main__":
    app.run(debug=True)