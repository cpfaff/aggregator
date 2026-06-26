"""Regression tests for the Celery task-monitor CLI (B19).

When the broker/workers are unreachable, `celery inspect active --json` exits
with empty stdout and an error on stderr. run_celery_command used to return a
{"output", "error"} dict, which list_tasks/cancel_all_tasks misread as a
worker->tasks mapping and crashed with TypeError. The monitor is run precisely
when workers are down, so it must degrade gracefully.
"""

from types import SimpleNamespace
from unittest import mock

from app.utils import manage_tasks


def _broker_down_proc():
    return SimpleNamespace(
        stdout="",
        stderr="Error: Could not connect to the message broker.",
        returncode=69,
    )


def test_run_celery_command_empty_stdout_returns_none():
    """json command with empty stdout must not return an iterable-mapping shape."""
    with mock.patch.object(manage_tasks.subprocess, "run", return_value=_broker_down_proc()):
        assert manage_tasks.run_celery_command(["inspect", "active"]) is None


def test_list_tasks_does_not_crash_when_broker_down(capsys):
    with mock.patch.object(manage_tasks.subprocess, "run", return_value=_broker_down_proc()):
        manage_tasks.list_tasks(show_all=False)  # must not raise
    assert "Could not retrieve active tasks" in capsys.readouterr().out


def test_cancel_all_tasks_does_not_crash_when_broker_down(capsys):
    with mock.patch.object(manage_tasks.subprocess, "run", return_value=_broker_down_proc()):
        manage_tasks.cancel_all_tasks(force=False)  # must not raise
    assert "Could not retrieve active tasks" in capsys.readouterr().out


def test_cancel_task_uses_argv_not_shell():
    """A malicious task_id must reach subprocess as one unsplit argv element.

    cancel_task interpolates the operator-supplied task_id into the celery
    control command. With shell=True an f-string'd task_id like "$(touch
    /tmp/pwn)" is re-interpreted by the shell (command injection). The fix runs
    the celery control command as a list-argv with shell!=True, so the task_id
    is a single argument the shell never parses (REQ-SUB-1, RH-11).
    """
    injection = "$(touch /tmp/pwn)"
    spy = mock.Mock(return_value=SimpleNamespace(stdout="ok", stderr="", returncode=0))
    with mock.patch.object(manage_tasks.subprocess, "run", spy):
        manage_tasks.cancel_task(injection, force_terminate=False)

    assert spy.call_args.kwargs.get("shell") is not True
    argv = spy.call_args.args[0]
    assert isinstance(argv, (list, tuple))
    assert injection in argv


def _cancel_failed_proc():
    """A celery control command that exited non-zero (e.g. task not found)."""
    return SimpleNamespace(stdout="", stderr="Error: task not found", returncode=1)


def test_cancel_task_reports_failure_on_nonzero_exit(capsys):
    """A non-zero celery exit must surface as a failure, not a success (REQ-SUB-2).

    The non-JSON path returned an always-truthy {"output", "error"} dict without
    inspecting returncode, so cancel_task's `if result:` fired the "revoked"
    success branch even when the celery child exited non-zero. Keying off
    returncode (mirroring the es_gateway down-path-to-None discipline) lets
    cancel_task's `if not result:` failure branch fire instead.
    """
    with mock.patch.object(manage_tasks.subprocess, "run", return_value=_cancel_failed_proc()):
        manage_tasks.cancel_task("abc", force_terminate=False)
    out = capsys.readouterr().out
    assert "❌ Failed to cancel task" in out
    assert "✅" not in out


def test_cancel_task_success_on_zero_exit(capsys):
    """A zero-exit command still reports success — returncode, not stderr, decides."""
    zero_exit = SimpleNamespace(stdout="ok", stderr="harmless warning", returncode=0)
    with mock.patch.object(manage_tasks.subprocess, "run", return_value=zero_exit):
        manage_tasks.cancel_task("abc", force_terminate=False)
    out = capsys.readouterr().out
    assert "✅ Task abc has been revoked" in out
    assert "❌ Failed to cancel task" not in out
