from flask import Flask, render_template, request, redirect, url_for
from utils.db import init_db, add_deployment, get_all_deployments
from utils.port_manager import get_next_available_port

app = Flask(__name__)

init_db()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/deploy", methods=["POST"])
def deploy():
    student_name = request.form.get("student_name")
    project_name = request.form.get("project_name")

    if not student_name or not project_name:
        return "Missing required fields", 400

    assigned_port = get_next_available_port()
    route_path = f"/apps/{project_name}"
    container_name = f"{project_name}-container"

    add_deployment(
        student_name=student_name,
        project_name=project_name,
        assigned_port=assigned_port,
        route_path=route_path,
        container_name=container_name,
        status="Registered"
    )

    return redirect(url_for("deployments"))

@app.route("/deployments")
def deployments():
    deployment_list = get_all_deployments()
    return render_template("deployments.html", deployments=deployment_list)

@app.route("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)