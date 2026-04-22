from utils.db import get_all_deployments

def get_next_available_port(start_port=8000):
    deployments = get_all_deployments()
    used_ports = [item["assigned_port"] for item in deployments]

    port = start_port
    while port in used_ports:
        port += 1

    return port