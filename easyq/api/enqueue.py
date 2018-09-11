from datetime import datetime, timezone

from flask import Blueprint, current_app, g, make_response, request
from rq_scheduler import Scheduler

from easyq.models.task import Task
from easyq.utils import parse_time
from easyq.worker.job import run_job

try:
    from ujson import dumps, loads
except ImportError:
    from json import dumps, loads

bp = Blueprint('enqueue', __name__)


@bp.route('/tasks/<task_id>', methods=('POST', ))
def create_task(task_id):
    details = request.json

    if details is None and request.data is not None:
        details = loads(request.data)

    if details is None or details == '':
        msg = 'Failed to enqueue task because JSON body could not be parsed.'
        g.logger.warn(msg)

        return make_response(
            msg,
            400,
        )

    image = details.get('image', None)
    command = details.get('command', None)

    if image is None or command is None:
        return make_response(
            'image and command must be filled in the request.',
            400,
        )

    logger = g.logger.bind(task_id=task_id, image=image, command=command)

    logger.debug('Creating task...')
    task = Task.objects(task_id=task_id).modify(
        task_id=task_id, upsert=True, new=True)
    logger.info('Task created successfully.')

    logger.debug('Creating job...')
    j = task.create_job()
    job_id = str(j.id)
    logger.debug('Job created successfully...', job_id=job_id)

    queue_job_id = None

    start_at = details.get('startAt', None)
    start_in = parse_time(details.get('startIn', None))
    cron = details.get('cron', None)
    scheduler = Scheduler('jobs', connection=current_app.redis)

    if start_at is not None:
        dt = datetime.utcfromtimestamp(int(start_at))
        logger.debug('Enqueuing job execution in the future...', start_at=dt)
        result = scheduler.enqueue_at(dt, run_job, task_id, job_id, image,
                                      command)
        j.metadata['enqueued_id'] = result.id
        j.save()
        logger.info('Job execution enqueued successfully.', start_at=dt)
    elif start_in is not None:
        dt = datetime.now(tz=timezone.utc) + start_in
        logger.debug('Enqueuing job execution in the future...', start_at=dt)
        result = scheduler.enqueue_at(dt, run_job, task_id, job_id, image,
                                      command)
        j.metadata['enqueued_id'] = result.id
        j.save()
        logger.info('Job execution enqueued successfully.', start_at=dt)
    elif cron is not None:
        logger.debug('Enqueuing job execution using cron...', cron=cron)
        result = scheduler.cron(
            cron,  # A cron string (e.g. "0 0 * * 0")
            func=run_job,
            args=[task_id, job_id, image, command],
            repeat=None,
            queue_name='jobs',
        )
        j.metadata['enqueued_id'] = result.id
        j.save()
        logger.info('Job execution enqueued successfully.', cron=cron)
    else:
        logger.debug('Enqueuing job execution...')
        result = current_app.job_queue.enqueue(
            run_job, task_id, job_id, image, command, timeout=-1)
        queue_job_id = result.id
        j.metadata['enqueued_id'] = result.id
        j.save()
        logger.info('Job execution enqueued successfully.')

    return dumps({
        "taskId": task_id,
        "jobId": job_id,
        "queueJobId": queue_job_id,
    })
