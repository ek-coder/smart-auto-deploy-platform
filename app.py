from flask import Flask, render_template, request, redirect, url_for, jsonify
from utils.db import init_db, add_deployment, get_all_deployments
from utils.port_manager import get_next_available_port
import shutil
import subprocess
import re
from pathlib import Path

app = Flask(__name__)

init_db()

BASE_DIR = Path("/app")
DEPLOYMENTS_DIR = BASE_DIR / "deployments"
NGINX_ROUTES_DIR = Path("/nginx-routes")


def sanitize_name(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name or "project"


def create_nginx_route(project_name: str, assigned_port: int) -> None:
    NGINX_ROUTES_DIR.mkdir(parents=True, exist_ok=True)
    route_file = NGINX_ROUTES_DIR / f"{project_name}.conf"

    config = f"""
location /apps/{project_name}/ {{
    proxy_pass http://localhost:{assigned_port}/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}}
""".strip()

    route_file.write_text(config, encoding="utf-8")


def run_command(command, cwd=None):
    return subprocess.run(command, capture_output=True, text=True, cwd=cwd)


def deploy_project(student_name: str, project_name_raw: str, repo_url: str):
    project_name = sanitize_name(project_name_raw)
    assigned_port = get_next_available_port(start_port=8100)
    route_path = f"/apps/{project_name}"
    container_name = f"{project_name}-container"
    image_name = f"{project_name}-image"
    project_dir = DEPLOYMENTS_DIR / project_name

    if project_dir.exists():
        shutil.rmtree(project_dir)

    # Clone repo
    clone_result = run_command(["git", "clone", repo_url, str(project_dir)])
    if clone_result.returncode != 0:
        return False, f"Git clone failed:\n{clone_result.stderr}"

    # Remove old container if exists
    run_command(["docker", "rm", "-f", container_name])

    # Remove old image if exists
    run_command(["docker", "rmi", "-f", image_name])

    # Build image
    build_result = run_command(["docker", "build", "-t", image_name, "."], cwd=str(project_dir))
    if build_result.returncode != 0:
        return False, f"Build failed:\n{build_result.stderr}"

    # Run container
    run_result = run_command([
        "docker", "run", "-d",
        "-p", f"{assigned_port}:8000",
        "--name", container_name,
        image_name
    ])
    if run_result.returncode != 0:
        return False, f"Container run failed:\n{run_result.stderr}"

    # Write nginx route
    create_nginx_route(project_name, assigned_port)

    add_deployment(
        student_name=student_name,
        project_name=project_name,
        assigned_port=assigned_port,
        route_path=route_path,
        container_name=container_name,
        status="Running"
    )

    return True, {
        "project_name": project_name,
        "assigned_port": assigned_port,
        "route_path": route_path,
        "container_name": container_name
    }


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/deploy", methods=["POST"])
def deploy():
    student_name = request.form.get("student_name", "").strip()
    project_name = request.form.get("project_name", "").strip()
    repo_url = request.form.get("repo_url", "").strip()

    if not student_name or not project_name or not repo_url:
        return "Missing required fields", 400

    success, result = deploy_project(student_name, project_name, repo_url)

    if not success:
        return f"<pre>{result}</pre>", 500

    return redirect(url_for("deployments"))


@app.route("/api/deploy", methods=["POST"])
def api_deploy():
    data = request.get_json(silent=True) or {}

    student_name = str(data.get("student_name", "")).strip()
    project_name = str(data.get("project_name", "")).strip()
    repo_url = str(data.get("repo_url", "")).strip()

    if not student_name or not project_name or not repo_url:
        return jsonify({
            "success": False,
            "message": "student_name, project_name, and repo_url are required"
        }), 400

    success, result = deploy_project(student_name, project_name, repo_url)

    if not success:
        return jsonify({
            "success": False,
            "message": result
        }), 500

    return jsonify({
        "success": True,
        "message": "Deployment successful",
        "data": result
    }), 200


@app.route("/deployments")
def deployments():
    deployment_list = get_all_deployments()
    return render_template("deployments.html", deployments=deployment_list)


@app.route("/health")
def health():
    return {"status": "ok", "service": "dashboard"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)