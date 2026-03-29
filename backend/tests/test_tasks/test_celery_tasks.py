"""Tests for Celery application configuration.

These tests verify the Celery config without requiring a live Redis broker.
We mock the Celery app at the module level so no connection is attempted.
"""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Celery app configuration
# ---------------------------------------------------------------------------

def test_celery_task_routes_preprocessing():
    """preprocessing tasks must be routed to the 'preprocessing' queue."""
    with patch("celery.Celery.autodiscover_tasks"):
        from app.tasks.celery_app import celery_app

    routes = celery_app.conf.task_routes
    assert "app.tasks.preprocessing.*" in routes
    assert routes["app.tasks.preprocessing.*"]["queue"] == "preprocessing"


def test_celery_task_routes_training():
    """training tasks must be routed to the 'training' queue."""
    with patch("celery.Celery.autodiscover_tasks"):
        from app.tasks.celery_app import celery_app

    routes = celery_app.conf.task_routes
    assert "app.tasks.training.*" in routes
    assert routes["app.tasks.training.*"]["queue"] == "training"


def test_celery_default_queue():
    with patch("celery.Celery.autodiscover_tasks"):
        from app.tasks.celery_app import celery_app

    assert celery_app.conf.task_default_queue == "default"


def test_celery_serializers():
    with patch("celery.Celery.autodiscover_tasks"):
        from app.tasks.celery_app import celery_app

    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert "json" in celery_app.conf.accept_content


def test_celery_utc_timezone():
    with patch("celery.Celery.autodiscover_tasks"):
        from app.tasks.celery_app import celery_app

    assert celery_app.conf.enable_utc is True
    assert celery_app.conf.timezone == "UTC"


def test_celery_task_track_started():
    with patch("celery.Celery.autodiscover_tasks"):
        from app.tasks.celery_app import celery_app

    assert celery_app.conf.task_track_started is True


def test_celery_late_acks():
    """task_acks_late ensures tasks are re-queued if the worker crashes mid-execution."""
    with patch("celery.Celery.autodiscover_tasks"):
        from app.tasks.celery_app import celery_app

    assert celery_app.conf.task_acks_late is True


def test_celery_prefetch_multiplier():
    """Prefetch multiplier=1 prevents workers from grabbing too many tasks at once."""
    with patch("celery.Celery.autodiscover_tasks"):
        from app.tasks.celery_app import celery_app

    assert celery_app.conf.worker_prefetch_multiplier == 1


def test_celery_app_name():
    with patch("celery.Celery.autodiscover_tasks"):
        from app.tasks.celery_app import celery_app

    assert celery_app.main == "atlas_vox"


# ---------------------------------------------------------------------------
# Task registration — verify tasks exist as registered Celery tasks
# ---------------------------------------------------------------------------

def test_train_model_task_exists():
    """train_model must be importable and registered as a Celery task."""
    # Import the task module; Celery registers tasks at import time.
    # We don't need Redis — just verify the task object is present.
    from app.tasks.training import train_model

    # Celery tasks have a .delay attribute and a .name attribute
    assert hasattr(train_model, "delay"), "train_model must be a Celery task (missing .delay)"
    assert hasattr(train_model, "name"), "train_model must be a Celery task (missing .name)"
    assert "train_model" in train_model.name


def test_preprocess_samples_task_exists():
    """preprocess_samples must be importable and registered as a Celery task."""
    from app.tasks.preprocessing import preprocess_samples

    assert hasattr(preprocess_samples, "delay"), "preprocess_samples must be a Celery task (missing .delay)"
    assert hasattr(preprocess_samples, "name"), "preprocess_samples must be a Celery task (missing .name)"
    assert "preprocess_samples" in preprocess_samples.name


# ---------------------------------------------------------------------------
# Function signatures — verify expected parameters without running tasks
# ---------------------------------------------------------------------------

def test_train_model_function_signature():
    """train_model must accept a job_id positional parameter."""
    from app.tasks.training import train_model

    # Celery bind=True tasks wrap the original function; access via __wrapped__
    # or inspect the underlying callable's run method.
    # The Celery task's run method reflects the original signature.
    sig = inspect.signature(train_model.run)
    param_names = list(sig.parameters.keys())
    # bind=True means first param is `self`, second is the user param
    assert "job_id" in param_names, (
        f"train_model.run must accept 'job_id' parameter, got: {param_names}"
    )


def test_preprocess_samples_function_signature():
    """preprocess_samples must accept a profile_id positional parameter."""
    from app.tasks.preprocessing import preprocess_samples

    sig = inspect.signature(preprocess_samples.run)
    param_names = list(sig.parameters.keys())
    assert "profile_id" in param_names, (
        f"preprocess_samples.run must accept 'profile_id' parameter, got: {param_names}"
    )


# ---------------------------------------------------------------------------
# Task delay() is mockable — guard against API changes
# ---------------------------------------------------------------------------

def test_train_model_delay_is_callable():
    """Verify train_model.delay is callable — callers rely on this API."""
    from app.tasks.training import train_model

    assert callable(train_model.delay)


def test_preprocess_samples_delay_is_callable():
    """Verify preprocess_samples.delay is callable."""
    from app.tasks.preprocessing import preprocess_samples

    assert callable(preprocess_samples.delay)


# ---------------------------------------------------------------------------
# Reliability / retry configuration
# ---------------------------------------------------------------------------

def test_celery_result_expires():
    """Results should expire after 24 hours."""
    from app.tasks.celery_app import celery_app
    assert celery_app.conf.result_expires == 86400


def test_celery_reject_on_worker_lost():
    from app.tasks.celery_app import celery_app
    assert celery_app.conf.task_reject_on_worker_lost is True


def test_celery_default_retry_delay():
    from app.tasks.celery_app import celery_app
    assert celery_app.conf.task_default_retry_delay == 60


def test_celery_max_retries():
    from app.tasks.celery_app import celery_app
    assert celery_app.conf.task_max_retries == 3
