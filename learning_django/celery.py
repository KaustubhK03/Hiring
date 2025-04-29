# my_project/celery.py
from __future__ import absolute_import
import os
from celery import Celery, Task
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'learning_django.settings') 

app = Celery('learning_django') 

app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# Load the celery beat scheduler
app.conf.beat_scheduler = "django_celery_beat.schedulers.DatabaseScheduler"

# Optional, but recommended: Define a custom task class for retry behavior
class MyTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        print(f"Task {task_id} failed: {exc}")
        # Implement retry logic here if needed, e.g.,
        self.retry(exc=exc, countdown=60)  # Retry after 60 seconds
        # Or log the error, send a notification, etc.


app.Task = MyTask  # Use the custom task class
