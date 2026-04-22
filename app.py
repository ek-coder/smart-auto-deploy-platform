from flask import Flask, render_template, request, redirect, url_for
from utils.db import init_db, add_deployment, get_all_deployments
from utils.port_manager import get_next_available_port
import os
import re
import shutil
import subprocess
from pathlib import Path

app = Flask(__name__)

# Initialize database
init_db()

# Base paths inside the dashboard container
BASE_DIR = Path("/app")
DEPLOYMENTS_DIR = BASE_DIR / "deployments"


def sanitize_name(name: str) -> str:
    """
    Convert project name into safe lowercase slug for folder/image/container names.
    Example: 'Quiz App 1' -> 'quiz-app-1'
    """
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name or "project"


def create_project_files(project_dir: Path, project_name: str, student_name: str) -> None:
    """
    Create a simple deployable Flask app inside deployments/<project_name>.
    This is safer than copying the dashboard project into itself.
    """
    templates_dir = project_dir / "templates"
    static_dir = project_dir / "static"

    templates_dir.mkdir(parents=True, exist_ok=True)
    static_dir.mkdir(parents=True, exist_ok=True)

    app_py = f"""from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/health")
def health():
    return {{"status": "ok", "project": "{project_name}"}}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
"""

    requirements_txt = "Flask\ngunicorn\n"

    dockerfile = """FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "app.py"]
"""

    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name}</title>
    <link rel="stylesheet" href="{{{{ url_for('static', filename='style.css') }}}}">
</head>
<body>
    <div class="page">
        <div class="card">
            <h1>{project_name}</h1>
            <p>Deployed automatically by Smart Auto Deploy Platform</p>
            <p><strong>Student:</strong> {student_name}</p>
            <p><strong>Status:</strong> Running</p>
        </div>
    </div>
</body>
</html>
"""

    style_css = """body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: linear-gradient(135deg, #0f172a, #1e293b);
    color: white;
}

.page {
    min-height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
}

.card {
    width: 500px;
    background: rgba(255, 255, 255, 0.08);
    backdrop-filter: blur(12px);
    border-radius: 18px;
    padding: 30px;
    text-align: center;
    box-shadow: 0 8px 30px rgba(0,0,0,0.25);
}

h1 {
    margin-bottom: 14px;
}
"""

    (project_dir / "app.py").write_text(app_py, encoding="utf-8")
    (project_dir / "requirements.txt").write_text(requirements_txt, encoding="utf-8")
    (project_dir / "Dockerfile").write_text(dockerfile, encoding="utf-8")
    (templates_dir / "index.html").write_text(index_html, encoding="utf-8")
    (static_dir / "style.css").write_text(style_css, encoding="utf-8")


def run_command(command: list[str]) -> subprocess.CompletedProcess:
    """
    Run shell command and capture output for debugging.
    """
    return subprocess.run(command, capture_output=True, text=True)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/deploy", methods=["POST"])
def deploy():
    student_name = request.form.get("student_name", "").strip()
    project_name_raw = request.form.get("project_name", "").strip()

    if not student_name or not project_name_raw:
        return "Missing required fields", 400

    project_name = sanitize_name(project_name_raw)
    assigned_port = get_next_available_port(start_port=8100)
    route_path = f"/apps/{project_name}"
    container_name = f"{project_name}-container"
    image_name = f"{project_name}-image"
    project_dir = DEPLOYMENTS_DIR / project_name

    try:
        # Fresh project directory
        if project_dir.exists():
            shutil.rmtree(project_dir)
        project_dir.mkdir(parents=True, exist_ok=True)

        # Create a simple student app
        create_project_files(project_dir, project_name_raw, student_name)

        # Remove old container if it exists
        run_command(["docker", "rm", "-f", container_name])

        # Build image
        build_result = run_command([
            "docker", "build", "-t", image_name, str(project_dir)
        ])

        if build_result.returncode != 0:
            return (
                f"Build failed:<br><pre>{build_result.stderr}</pre>",
                500,
            )

        # Run container
        run_result = run_command([
            "docker", "run", "-d",
            "-p", f"{assigned_port}:8000",
            "--name", container_name,
            image_name
        ])

        if run_result.returncode != 0:
            return (
                f"Container run failed:<br><pre>{run_result.stderr}</pre>",
                500,
            )

        # Save deployment record
        add_deployment(
            student_name=student_name,
            project_name=project_name,
            assigned_port=assigned_port,
            route_path=route_path,
            container_name=container_name,
            status="Running"
        )

        return redirect(url_for("deployments"))

    except Exception as e:
        return f"Deployment error: {str(e)}", 500


@app.route("/deployments")
def deployments():
    deployment_list = get_all_deployments()
    return render_template("deployments.html", deployments=deployment_list)


@app.route("/health")
def health():
    return {"status": "ok", "service": "dashboard"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)