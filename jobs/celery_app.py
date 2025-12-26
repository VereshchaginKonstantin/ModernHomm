#!/usr/bin/env python3
"""
Celery application configuration for ModernHomm background jobs.
"""

import os
from celery import Celery

# Redis connection URL
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')

# Create Celery app
celery_app = Celery(
    'modernhomm_jobs',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['jobs.tasks']
)

# Celery configuration
celery_app.conf.update(
    # Timezone
    timezone='UTC',
    enable_utc=True,

    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',

    # Beat schedule for periodic tasks
    beat_schedule={
        'hourly-recruit-accumulate': {
            'task': 'jobs.tasks.hourly_recruit_accumulate',
            'schedule': 3600.0,  # Every hour (3600 seconds)
        },
        'daily-reset-limits': {
            'task': 'jobs.tasks.daily_reset_limits',
            'schedule': {
                'hour': 0,
                'minute': 0,
            },
        },
    },

    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,

    # Result backend settings
    result_expires=86400,  # Results expire after 24 hours
)

# Use crontab for daily tasks
from celery.schedules import crontab
celery_app.conf.beat_schedule['daily-reset-limits']['schedule'] = crontab(hour=0, minute=0)

if __name__ == '__main__':
    celery_app.start()
