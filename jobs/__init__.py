#!/usr/bin/env python3
"""
Background jobs module for ModernHomm.
Uses Celery with Redis for task scheduling.
"""

from .reset_unit_limits import reset_daily_unit_limits, initialize_user_unit_limits

# Celery imports (only when celery is available)
try:
    from .celery_app import celery_app
    from .tasks import hourly_recruit_accumulate, daily_reset_limits
    __all__ = [
        'reset_daily_unit_limits', 'initialize_user_unit_limits',
        'celery_app', 'hourly_recruit_accumulate', 'daily_reset_limits'
    ]
except ImportError:
    __all__ = ['reset_daily_unit_limits', 'initialize_user_unit_limits']
