from flask import Flask, render_template
import docker

app = Flask(__name__)
client = docker.from_env()

# List the container names you want to track
EXPECTED_CONTAINERS = [
    "ci-weight_app-1",
    "ci-weight_db1-1",
    "ci-weight_app_test-1",
    "ci-weight_db1_test-1"
]

@app.route("/")
def index():
    # Get all containers (running and stopped)
    containers = client.containers.list(all=True)
    status_map = {container.name: container.status for container in containers}

    # Build status list
    container_statuses = []
    for name in EXPECTED_CONTAINERS:
        status = status_map.get(name, "exited")  # If not found, assume "exited"
        container_statuses.append({"name": name, "status": status})

    return render_template("index.html", containers=container_statuses)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8090, debug=True)