#!/usr/bin/env python3
"""
Celery tasks for ModernHomm background jobs.
"""

import os
import sys
import json
import logging
from datetime import datetime
from decimal import Decimal

# Add project path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from jobs.celery_app import celery_app
from db.repository import Database
from db.models import JobLog, UserRaceUnitLimit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('celery.tasks')

# Database connection
db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@postgres:5432/telegram_bot')
db = Database(db_url)


def log_job_start(job_name: str) -> int:
    """Record job start"""
    with db.get_session() as session:
        job_log = JobLog(
            job_name=job_name,
            status=JobLog.STATUS_RUNNING,
            started_at=datetime.utcnow()
        )
        session.add(job_log)
        session.commit()
        return job_log.id


def log_job_success(log_id: int, records_processed: int, details: dict = None):
    """Record successful job completion"""
    with db.get_session() as session:
        job_log = session.query(JobLog).filter_by(id=log_id).first()
        if job_log:
            job_log.status = JobLog.STATUS_SUCCESS
            job_log.finished_at = datetime.utcnow()
            job_log.records_processed = records_processed
            if job_log.started_at:
                delta = job_log.finished_at - job_log.started_at
                job_log.duration_ms = int(delta.total_seconds() * 1000)
            if details:
                job_log.details = json.dumps(details, ensure_ascii=False)
            session.commit()


def log_job_failure(log_id: int, error_message: str):
    """Record job failure"""
    with db.get_session() as session:
        job_log = session.query(JobLog).filter_by(id=log_id).first()
        if job_log:
            job_log.status = JobLog.STATUS_FAILED
            job_log.finished_at = datetime.utcnow()
            job_log.error_message = error_message
            if job_log.started_at:
                delta = job_log.finished_at - job_log.started_at
                job_log.duration_ms = int(delta.total_seconds() * 1000)
            session.commit()


@celery_app.task(bind=True, max_retries=3)
def hourly_recruit_accumulate(self):
    """
    Hourly unit recruitment accumulation.
    Runs every hour to add units based on daily_speed / 24.
    Compensates for missed hours since last update.
    """
    job_name = 'hourly_recruit_accumulate'
    log_id = log_job_start(job_name)

    try:
        logger.info(f"Starting job: {job_name}")
        updated_count = 0
        now = datetime.utcnow()

        with db.get_session() as session:
            # Find all unlocked limits
            limits = session.query(UserRaceUnitLimit).filter(
                UserRaceUnitLimit.level_unlocked == True
            ).all()

            for limit in limits:
                # Calculate hours passed since last update
                last_update = limit.last_accumulate_at or limit.created_at or now
                hours_passed = (now - last_update).total_seconds() / 3600.0

                # Skip if less than 1 hour passed (will be processed in next run)
                # Maximum 168 hours (7 days) to prevent overflow
                if hours_passed < 1.0:
                    continue
                hours_passed = min(hours_passed, 168.0)

                # Calculate hourly rate: daily_speed / 24
                hourly_rate = Decimal(str(limit.daily_speed)) / Decimal('24')

                # Add to accumulated fraction with hours compensation
                current_fraction = Decimal(str(limit.accumulated_fraction))
                rate_to_add = hourly_rate * Decimal(str(hours_passed))
                new_fraction = current_fraction + rate_to_add

                # Extract whole units to add to available_count
                units_to_add = int(new_fraction)
                remaining_fraction = new_fraction - units_to_add

                if units_to_add > 0 or current_fraction != remaining_fraction:
                    limit.accumulated_fraction = remaining_fraction
                    limit.available_count += units_to_add
                    limit.last_accumulate_at = now
                    limit.updated_at = now
                    updated_count += 1

            session.commit()

        logger.info(f"Job {job_name} completed: {updated_count} records updated")
        log_job_success(log_id, updated_count, {'message': f'Updated {updated_count} user race unit limits'})

        return {'status': 'success', 'updated': updated_count}

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Job {job_name} failed: {error_msg}")
        log_job_failure(log_id, error_msg)

        # Retry on failure
        raise self.retry(exc=e, countdown=60)


@celery_app.task(bind=True)
def daily_reset_limits(self):
    """
    Daily limits reset check.
    Runs once a day at 00:00 UTC.
    """
    job_name = 'daily_reset_limits'
    log_id = log_job_start(job_name)

    try:
        logger.info(f"Starting job: {job_name}")
        # This job can be used for additional checks
        # or manual limit resets

        log_job_success(log_id, 0, {'message': 'Daily check completed'})

        return {'status': 'success', 'message': 'Daily check completed'}

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Job {job_name} failed: {error_msg}")
        log_job_failure(log_id, error_msg)
        raise
