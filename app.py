from flask import Flask, render_template

app = Flask(__name__)

projects = [
    {
        "student": "Lakshay Verma",
        "project": "Weather App",
        "status": "Pending",
        "url": "Not deployed yet"
    },
    {
        "student": "Student 2",
        "project": "Quiz App",
        "status": "Pending",
        "url": "Not deployed yet"
    }
]

@app.route("/")
def home():
    return render_template("index.html", projects=projects)

@app.route("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)