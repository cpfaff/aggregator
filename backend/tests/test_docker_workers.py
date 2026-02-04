"""Test docker-compose worker configuration."""

import os
import subprocess


def test_docker_compose_validation():
    """Test that docker-compose.yml is valid."""
    result = subprocess.run(
        ["docker-compose", "-f", "../../docker-compose.yml", "config"],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(__file__),
    )
    assert result.returncode == 0, f"Docker compose config validation failed: {result.stderr}"

    # Check that both workers are defined in config
    assert "celery_worker_validation" in result.stdout
    assert "celery_worker_stats" in result.stdout
    assert "heavy_validation" in result.stdout
    assert "light_tasks" in result.stdout


def test_worker_memory_limits():
    """Test that workers have appropriate memory limits."""
    result = subprocess.run(
        ["docker-compose", "-f", "../../docker-compose.yml", "config"],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(__file__),
    )

    config_lines = result.stdout.split("\n")

    # Track which worker we're in
    in_validation_worker = False
    in_stats_worker = False
    validation_memory_found = False
    stats_memory_found = False

    for line in config_lines:
        if "celery_worker_validation:" in line:
            in_validation_worker = True
            in_stats_worker = False
        elif "celery_worker_stats:" in line:
            in_stats_worker = True
            in_validation_worker = False
        elif (
            line.strip().startswith("celery_")
            or line.strip().startswith("frontend:")
            or line.strip().startswith("backend:")
        ):
            in_validation_worker = False
            in_stats_worker = False

        # Check for memory limits (2G = 2147483648 bytes, 1G = 1073741824 bytes)
        if in_validation_worker and (
            "memory: 2G" in line or 'memory: "2147483648"' in line or "2147483648" in line
        ):
            validation_memory_found = True
        elif in_stats_worker and (
            "memory: 1G" in line or 'memory: "1073741824"' in line or "1073741824" in line
        ):
            stats_memory_found = True

    assert validation_memory_found, "Validation worker should have 2G memory limit"
    assert stats_memory_found, "Stats worker should have 1G memory limit"


def test_worker_health_checks():
    """Test that both workers have proper health checks configured."""
    result = subprocess.run(
        ["docker-compose", "-f", "../../docker-compose.yml", "config"],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(__file__),
    )

    config_lines = result.stdout.split("\n")

    # Check health check configuration for both workers
    validation_healthcheck_found = False
    stats_healthcheck_found = False
    in_validation_worker = False
    in_stats_worker = False

    for _i, line in enumerate(config_lines):
        if "celery_worker_validation:" in line:
            in_validation_worker = True
            in_stats_worker = False
        elif "celery_worker_stats:" in line:
            in_stats_worker = True
            in_validation_worker = False
        elif (
            line.strip().startswith("celery_")
            or line.strip().startswith("frontend:")
            or line.strip().startswith("backend:")
        ):
            in_validation_worker = False
            in_stats_worker = False

        if "celery -A app.core.celery_app inspect ping" in line:
            if in_validation_worker:
                validation_healthcheck_found = True
            elif in_stats_worker:
                stats_healthcheck_found = True

    assert validation_healthcheck_found, "Validation worker should have health check"
    assert stats_healthcheck_found, "Stats worker should have health check"


def test_worker_dependencies():
    """Test that workers have correct dependencies configured."""
    result = subprocess.run(
        ["docker-compose", "-f", "../../docker-compose.yml", "config"],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(__file__),
    )

    config = result.stdout

    # Both workers should depend on db and redis
    assert "depends_on:" in config

    # Find dependencies for each worker
    lines = config.split("\n")
    validation_deps_found = False
    stats_deps_found = False

    for i, line in enumerate(lines):
        # Match only top-level service definitions (2-space indent), not
        # references inside another service's depends_on block.
        if line.startswith("  celery_worker_validation:") and not line.startswith("      "):
            # Look for depends_on within the service block
            for j in range(i, min(i + 25, len(lines))):
                if "depends_on:" in lines[j]:
                    # Check next lines for db and redis
                    for k in range(j + 1, min(j + 10, len(lines))):
                        if "db" in lines[k] or "redis" in lines[k]:
                            validation_deps_found = True
                            break
                    break

        elif line.startswith("  celery_worker_stats:") and not line.startswith("      "):
            # Look for depends_on within the service block
            for j in range(i, min(i + 25, len(lines))):
                if "depends_on:" in lines[j]:
                    # Check next lines for db and redis
                    for k in range(j + 1, min(j + 10, len(lines))):
                        if "db" in lines[k] or "redis" in lines[k]:
                            stats_deps_found = True
                            break
                    break

    assert validation_deps_found, "Validation worker should depend on db and redis"
    assert stats_deps_found, "Stats worker should depend on db and redis"


def test_celery_beat_dependencies():
    """Test that celery-beat depends on both new workers."""
    result = subprocess.run(
        ["docker-compose", "-f", "../../docker-compose.yml", "config"],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(__file__),
    )

    lines = result.stdout.split("\n")
    beat_deps_correct = False

    for i, line in enumerate(lines):
        if "celery-beat:" in line:
            # Look for depends_on
            for j in range(i, min(i + 15, len(lines))):
                if "depends_on:" in lines[j]:
                    # Check for both workers in dependencies
                    deps_text = "\n".join(lines[j : j + 10])
                    if (
                        "celery_worker_validation" in deps_text
                        and "celery_worker_stats" in deps_text
                    ):
                        beat_deps_correct = True
                    break
            break

    assert beat_deps_correct, (
        "celery-beat should depend on both celery_worker_validation and celery_worker_stats"
    )


def test_worker_network_configuration():
    """Test that both workers are on the app-network."""
    result = subprocess.run(
        ["docker-compose", "-f", "../../docker-compose.yml", "config"],
        capture_output=True,
        text=True,
        cwd=os.path.dirname(__file__),
    )

    lines = result.stdout.split("\n")
    validation_network_found = False
    stats_network_found = False

    in_validation = False
    in_stats = False

    for line in lines:
        if "celery_worker_validation:" in line:
            in_validation = True
            in_stats = False
        elif "celery_worker_stats:" in line:
            in_stats = True
            in_validation = False
        elif line.strip() and not line.startswith(" "):
            in_validation = False
            in_stats = False

        if "app-network" in line:
            if in_validation:
                validation_network_found = True
            elif in_stats:
                stats_network_found = True

    assert validation_network_found, "Validation worker should be on app-network"
    assert stats_network_found, "Stats worker should be on app-network"


if __name__ == "__main__":
    # Run basic validation
    test_docker_compose_validation()
    test_worker_memory_limits()
    test_worker_health_checks()
    test_worker_dependencies()
    test_celery_beat_dependencies()
    test_worker_network_configuration()
    print("All docker-compose configuration tests passed!")
