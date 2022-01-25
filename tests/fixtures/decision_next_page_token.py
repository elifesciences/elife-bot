from datetime import datetime

EXPECTED = {
    "previousStartedEventId": 0,
    "workflowExecution": {
        "runId": "12ulEcVcpG651LIFXeyPeZXyVwGVcGVZynLJIJ1in8Nw0=",
        "workflowId": "sum_8983",
    },
    "startedEventId": 3,
    "workflowType": {"name": "Sum", "version": "1"},
    "events": [
        {
            "workflowExecutionStartedEventAttributes": {
                "taskStartToCloseTimeout": "60",
                "taskList": {"name": "DefaultTaskList"},
                "executionStartToCloseTimeout": "3600",
                "parentInitiatedEventId": 0,
                "workflowType": {"name": "Sum", "version": "1"},
                "input": '{"data": [1,3,7,11]}',
                "childPolicy": "TERMINATE",
            },
            "eventTimestamp": datetime(2013, 3, 21, 19, 19, 39, 266000),
            "eventType": "WorkflowExecutionStarted",
            "eventId": 1,
        }
    ],
    "taskToken": "AAAAKgAAAAEAAAAAAAAAAqAY4eiZJpVQEt1WPkz9MDTN0NZg7AjckLEWmUnn3uXP5Di+E3npzrVM9dmG7H7vZFRdBXUZCmHSMJikaeJfC0RSMZttsPlNI1mHHERYlBJJwSqFQ/p1wU3R59coiCxgvewOz0HUnygLBWNZFudXsxHS1+UWveoN74L8+MhVyo/n9nUrim8DU0l7yoosaR9QQsHguo890Q7D6chF0ru9ZQjvW2aDoY8IYJOQvLODepX5BwJ4zLd9bScNGhCgx7yJt9N200Zk4hlhLh3NAQqAuzmtNa0YFvmyRg5PtFAXs08G",
    "nextPageToken": "AAAAKgAAAAEAAAAAAAAAAtqAikiCfNvRQWL5o8LRag8VOjiC0ywRycaA+hrWMSOsycEGFOWUCY305yFylzkvj/91Uu05yzMyeJVs7cxeU3lBtMSz6mLH0f3+Es9mqLmR64vZ7vQYumIXEzmDB1YNxlwY971OP4kX2QFjWhufEOsYOzFKG5ImWc5FS/5BEnyPEbIbalSidAn1Jjf1qR6LaKCZkIEQMuyq9gKFjd6kMqPMc9SKHNY22xQTVIJyUf1wgw9m2YlWqqudcGPznF3oDt80OIBuxAUGk1/DN8p0fmW841tt50LJ2wXVdmvShrtjBMX6BW6ulNPUutBUaLXG/r9mY46NVntcOCQ/7+BIdzD0qal3xbjPGm0oJrHFZ8fIhe9VcGmQeRG52nN+jpgpqKZ2TFWMYNTkmquIw3fUvfbIu9k2FqMJSrgZ2m8dnIPN3ujm/uBXmNPSzuxWXMx0MxccqC+HuydVl15yMEuVnDfcqrUtupeRtftngYqEXyN0h1j7XC5th0EFQZb7SEKwZ7CQyFOKCwLModC+RxH6BwUydEdoRHDAIXYJqjAFAQ/XyJQTQCwVtX6JrmLUYG98s/w4ttdz/Ryb9VdHn+yNlAnpgrwOl/gB636yix+YU9igRITQgql2wj7YocGCWU7wNmykNI5yuIDwUjlurE8W7dnVsWhYwqPZi0qjh1KuuG2FyRBNonfdVEHN9cfj3QA/159Zh4C0ycsszTAPqpvAj/s+AiFZGJje1fiCum0OTikaV7gS2UvqZ91Ckc5c1yAGw3J7D4MFOSizbB1PIk2tReeoR43Nwq7jCSl16ryY+jdwScIAvwZXJ9/CAXzOIPAEJg==",
}
