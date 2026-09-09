from django.http import HttpResponse
from core.helpers.tasks import background_task
import time

@background_task
def slow_task():
    print("Slow task started")
    time.sleep(5)
    print("Slow task finished")

def test_view(request):
    print("View started")
    slow_task.delay()
    print("View finished")
    return HttpResponse("OK")
