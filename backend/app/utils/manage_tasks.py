#!/usr/bin/env python3
"""
Simple task management utility for monitoring and controlling Celery tasks.
Follows KISS principle - just shows what's running and lets you cancel tasks.
"""

import json
import subprocess
import sys
from datetime import datetime
from typing import Dict, Optional

# Add the app directory to path
sys.path.insert(0, "/app")


def run_celery_command(command: str, json_output: bool = True) -> Optional[Dict]:
    """Run a celery command and return the result."""
    cmd = f"celery -A app.core.celery_app {command}"
    if json_output:
        cmd += " --json"

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)

        if json_output and result.stdout:
            return json.loads(result.stdout)
        return {"output": result.stdout, "error": result.stderr}
    except subprocess.TimeoutExpired:
        print("⚠️  Command timed out after 10 seconds")
        return None
    except json.JSONDecodeError:
        print("⚠️  Failed to parse JSON output")
        return {"output": result.stdout, "error": result.stderr}
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return None


def format_duration(start_time: float) -> str:
    """Format duration from start time to now."""
    duration = datetime.now().timestamp() - start_time
    if duration < 60:
        return f"{duration:.0f}s"
    elif duration < 3600:
        return f"{duration / 60:.1f}m"
    else:
        return f"{duration / 3600:.1f}h"


def get_worker_type(worker_name: str) -> str:
    """Get human-friendly worker type from worker name."""
    # Map container hostnames to worker types
    # You can get these by running: docker exec <container> hostname
    worker_map = {
        "556860f53ba2": "VALIDATION Worker",
        "0241cccf1671": "STATISTICS Worker",
    }

    # Extract hostname from worker name (format: celery@hostname)
    hostname = worker_name.split("@")[1] if "@" in worker_name else worker_name

    return worker_map.get(hostname, f"Worker {hostname[:8]}")


def list_tasks(show_all: bool = False):
    """List currently running or all tasks."""
    print("=" * 70)
    print("TASK MONITOR - CELERY BACKGROUND TASKS")
    print("=" * 70)
    print()

    # Get active tasks
    print("🔄 RUNNING TASKS:")
    print("-" * 70)

    # Try to get active tasks from both workers
    # Note: Validation worker uses --pool=solo and may not respond to inspect
    active = run_celery_command("inspect active")
    if not active:
        print("❌ Could not retrieve active tasks from statistics worker")

    task_count = 0
    found_workers = set()

    # Process tasks from workers that respond
    if active:
        for worker, tasks in active.items():
            found_workers.add(worker)
            if tasks:
                worker_type = get_worker_type(worker)
                print(f"\n📦 {worker_type}:")
                for task in tasks:
                    task_count += 1
                    task_name = task["name"].replace("statistics.", "").replace("validator.", "")
                    duration = format_duration(task["time_start"])

                    print(
                        f"  [{task_count}] {task_name:<30} | ID: {task['id'][:8]}... | ⏱️  {duration}"
                    )

                    # Show relevant kwargs
                    if "kwargs" in task and task["kwargs"]:
                        params = []
                        for k, v in task["kwargs"].items():
                            if k in [
                                "batch_size",
                                "offset",
                                "dataset_id",
                                "provider_id",
                                "target_date",
                            ]:
                                params.append(f"{k}={v}")
                        if params:
                            print(f"      Parameters: {', '.join(params)}")

    # Check if validation worker is running but can't be inspected
    validation_worker_name = "celery@556860f53ba2"
    if validation_worker_name not in found_workers:
        print("\n⚠️  Note: VALIDATION Worker uses solo pool and cannot be inspected via Celery.")
        print("    Check Docker logs to see if validation tasks are running:")
        print("    docker logs -f searchgfbioorg-celery_worker_validation-1 --tail 20")

        # Try to check if validation is actually running by looking at recent logs
        try:
            result = subprocess.run(
                "docker logs searchgfbioorg-celery_worker_validation-1 --tail 5 2>&1 | grep -E '(received|Starting validation|Validation completed)' | tail -1",
                shell=True,
                capture_output=True,
                text=True,
                timeout=2,
            )
            if (
                result.stdout
                and "received" in result.stdout
                or "Starting validation" in result.stdout
            ):
                print("\n    🟡 Recent validation activity detected in logs")
        except:
            pass

    if task_count == 0 and validation_worker_name in found_workers:
        print("  ✅ No tasks currently running")
    elif task_count > 0:
        print(f"\n  Total: {task_count} active task(s) visible")

    # Get scheduled tasks (ETA/countdown)
    if show_all:
        print("\n\n⏰ SCHEDULED TASKS (waiting to run):")
        print("-" * 70)

        scheduled = run_celery_command("inspect scheduled")
        if scheduled:
            scheduled_count = 0
            for worker, tasks in scheduled.items():
                if tasks:
                    worker_type = get_worker_type(worker)
                    print(f"\n📦 {worker_type}:")
                    for task in tasks:
                        scheduled_count += 1
                        task_name = (
                            task["request"]["name"]
                            .replace("statistics.", "")
                            .replace("validator.", "")
                        )
                        eta = task.get("eta", "Unknown")
                        print(f"  [{scheduled_count}] {task_name:<30} | ETA: {eta}")

            if scheduled_count == 0:
                print("  ✅ No scheduled tasks")

        # Get reserved tasks (queued)
        print("\n\n📋 QUEUED TASKS (waiting for worker):")
        print("-" * 70)

        reserved = run_celery_command("inspect reserved")
        if reserved:
            queued_count = 0
            for worker, tasks in reserved.items():
                if tasks:
                    worker_type = get_worker_type(worker)
                    print(f"\n📦 {worker_type}:")
                    for task in tasks:
                        queued_count += 1
                        task_name = (
                            task["name"].replace("statistics.", "").replace("validator.", "")
                        )
                        print(f"  [{queued_count}] {task_name:<30}")

            if queued_count == 0:
                print("  ✅ No tasks in queue")

    print("\n" + "=" * 70)


def cancel_task(task_id: str, force_terminate: bool = False):
    """Cancel a specific task by ID."""
    print(f"🚫 Cancelling task {task_id}...")

    if force_terminate:
        # Use terminate to force kill the task (SIGTERM)
        result = run_celery_command(f"control terminate {task_id}", json_output=False)
        if result:
            print(f"⚡ Task {task_id} has been TERMINATED (force killed)")
            print("   Warning: This may leave resources in an inconsistent state.")
    else:
        # Use revoke which is gentler
        result = run_celery_command(f"control revoke {task_id} --terminate", json_output=False)
        if result:
            print(f"✅ Task {task_id} has been revoked")
            print("   Note: Running tasks will be terminated at the next checkpoint.")

    if not result:
        print(f"❌ Failed to cancel task {task_id}")


def cancel_all_tasks(force: bool = False):
    """Cancel all active and queued tasks."""
    print("⚠️  WARNING: This will cancel ALL running and queued tasks!")

    # Get all active tasks
    active = run_celery_command("inspect active")
    if not active:
        print("❌ Could not retrieve active tasks")
        return

    task_ids = []
    task_details = []
    for worker, tasks in active.items():
        for task in tasks:
            task_ids.append(task["id"])
            task_details.append((task["id"], task["name"]))

    # Get all reserved tasks
    reserved = run_celery_command("inspect reserved")
    if reserved:
        for worker, tasks in reserved.items():
            for task in tasks:
                task_ids.append(task["id"])
                task_details.append((task["id"], task.get("name", "queued")))

    if not task_ids:
        print("✅ No tasks to cancel")
        return

    print(f"\n🚫 Cancelling {len(task_ids)} task(s)...")

    if force:
        print("   Using FORCE TERMINATE (may leave resources inconsistent)")

    for task_id, task_name in task_details:
        if force:
            # Force terminate for stuck tasks
            result = run_celery_command(f"control terminate {task_id}", json_output=False)
            if result:
                print(f"  ⚡ TERMINATED: {task_id[:8]}... ({task_name.split('.')[-1]})")
        else:
            # Regular revoke with terminate flag
            result = run_celery_command(f"control revoke {task_id} --terminate", json_output=False)
            if result:
                print(f"  ✅ Revoked: {task_id[:8]}... ({task_name.split('.')[-1]})")

    if force:
        print(f"\n⚡ All {len(task_ids)} tasks have been FORCE TERMINATED")
        print("   Note: You may need to restart workers if they become unresponsive")
    else:
        print(f"\n✅ All {len(task_ids)} tasks have been revoked")
        print("   Note: Running tasks will terminate at the next checkpoint")


def check_workers():
    """Check worker health status."""
    print("🏥 WORKER HEALTH CHECK")
    print("=" * 70)

    # Ping workers
    result = run_celery_command("inspect ping")
    if result:
        for worker, status in result.items():
            worker_type = get_worker_type(worker)
            if status.get("ok") == "pong":
                print(f"✅ {worker_type}: Healthy")
            else:
                print(f"❌ {worker_type}: Not responding")
    else:
        print("❌ No workers responding")

    # Get worker stats
    print("\n📊 WORKER STATISTICS:")
    print("-" * 70)

    stats = run_celery_command("inspect stats")
    if stats:
        for worker, info in stats.items():
            if info:
                worker_type = get_worker_type(worker)
                pool = info.get("pool", {})
                total = info.get("total", {})

                # Count completed tasks based on worker type
                if "VALIDATION" in worker_type:
                    completed = sum(
                        v
                        for k, v in total.items()
                        if k.startswith("tasks.validator.") and isinstance(v, (int, float))
                    )
                else:
                    completed = sum(
                        v
                        for k, v in total.items()
                        if k.startswith("tasks.statistics.") and isinstance(v, (int, float))
                    )

                print(f"\n📦 {worker_type}:")
                print(f"  • Pool size: {pool.get('max-concurrency', 'N/A')}")
                print(f"  • Tasks completed: {completed}")
                print(f"  • Uptime: {info.get('clock', 'N/A')} seconds")

    print("\n" + "=" * 70)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Simple Celery task manager")
    parser.add_argument("--list", action="store_true", help="List running tasks")
    parser.add_argument(
        "--list-all", action="store_true", help="List all tasks (running, scheduled, queued)"
    )
    parser.add_argument("--cancel", type=str, help="Cancel a specific task by ID")
    parser.add_argument("--cancel-all", action="store_true", help="Cancel ALL tasks")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force terminate tasks (use with --cancel or --cancel-all)",
    )
    parser.add_argument("--health", action="store_true", help="Check worker health")

    args = parser.parse_args()

    # Default to listing tasks if no args
    if not any([args.list, args.list_all, args.cancel, args.cancel_all, args.health]):
        args.list = True

    if args.list or args.list_all:
        list_tasks(show_all=args.list_all)
    elif args.cancel:
        cancel_task(args.cancel, force_terminate=args.force)
    elif args.cancel_all:
        cancel_all_tasks(force=args.force)
    elif args.health:
        check_workers()

    return 0


if __name__ == "__main__":
    sys.exit(main())
