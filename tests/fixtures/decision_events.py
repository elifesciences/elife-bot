from datetime import datetime


EXPECTED = {
    "events": [
        {
            "eventTimestamp": datetime(2013, 3, 21, 19, 17, 50, 379000),
            "eventType": "WorkflowExecutionStarted",
            "workflowExecutionStartedEventAttributes": {
                "childPolicy": "TERMINATE",
                "input": '{"data": [1,3,7,11]}',
                "taskList": {"name": "DefaultTaskList"},
                "workflowType": {"version": "1", "name": "Sum"},
                "executionStartToCloseTimeout": "3600",
                "taskStartToCloseTimeout": "60",
                "parentInitiatedEventId": 0,
            },
            "eventId": 1,
        },
        {
            "eventType": "DecisionTaskScheduled",
            "decisionTaskScheduledEventAttributes": {
                "startToCloseTimeout": "60",
                "taskList": {"name": "DefaultTaskList"},
            },
            "eventTimestamp": datetime(2013, 3, 21, 19, 17, 50, 379000),
            "eventId": 2,
        },
        {
            "eventType": "DecisionTaskStarted",
            "decisionTaskStartedEventAttributes": {
                "identity": "decider_801",
                "scheduledEventId": 2,
            },
            "eventTimestamp": datetime(2013, 3, 21, 19, 17, 50, 467000),
            "eventId": 3,
        },
        {
            "eventType": "DecisionTaskCompleted",
            "eventTimestamp": datetime(2013, 3, 21, 19, 17, 50, 698000),
            "decisionTaskCompletedEventAttributes": {
                "startedEventId": 3,
                "scheduledEventId": 2,
            },
            "eventId": 4,
        },
        {
            "eventType": "ActivityTaskScheduled",
            "activityTaskScheduledEventAttributes": {
                "input": "null",
                "activityType": {"version": "1", "name": "PingWorker"},
                "taskList": {"name": "DefaultTaskList"},
                "heartbeatTimeout": "300",
                "scheduleToStartTimeout": "300",
                "control": "control data",
                "startToCloseTimeout": "300",
                "decisionTaskCompletedEventId": 4,
                "activityId": "PingWorker",
                "scheduleToCloseTimeout": "300",
            },
            "eventTimestamp": datetime(2013, 3, 21, 19, 17, 50, 698000),
            "eventId": 5,
        },
        {
            "eventType": "ActivityTaskScheduled",
            "activityTaskScheduledEventAttributes": {
                "input": '{"data": [1, 3, 7, 11]}',
                "activityType": {"version": "1", "name": "Sum"},
                "taskList": {"name": "DefaultTaskList"},
                "heartbeatTimeout": "300",
                "scheduleToStartTimeout": "300",
                "control": "control data",
                "startToCloseTimeout": "300",
                "decisionTaskCompletedEventId": 4,
                "activityId": "Sum2a",
                "scheduleToCloseTimeout": "300",
            },
            "eventTimestamp": datetime(2013, 3, 21, 19, 17, 50, 698000),
            "eventId": 6,
        },
        {
            "eventType": "ActivityTaskStarted",
            "eventTimestamp": datetime(2013, 3, 21, 19, 17, 50, 760000),
            "activityTaskStartedEventAttributes": {
                "identity": "worker_461",
                "scheduledEventId": 5,
            },
            "eventId": 7,
        },
        {
            "eventType": "ActivityTaskStarted",
            "eventTimestamp": datetime(2013, 3, 21, 19, 17, 50, 774000),
            "activityTaskStartedEventAttributes": {
                "identity": "worker_590",
                "scheduledEventId": 6,
            },
            "eventId": 8,
        },
        {
            "eventTimestamp": datetime(2013, 3, 21, 19, 17, 50, 932000),
            "eventType": "ActivityTaskCompleted",
            "activityTaskCompletedEventAttributes": {
                "startedEventId": 7,
                "result": "True",
                "scheduledEventId": 5,
            },
            "eventId": 9,
        },
        {
            "eventType": "DecisionTaskScheduled",
            "decisionTaskScheduledEventAttributes": {
                "startToCloseTimeout": "60",
                "taskList": {"name": "DefaultTaskList"},
            },
            "eventTimestamp": datetime(2013, 3, 21, 19, 17, 50, 932000),
            "eventId": 10,
        },
        {
            "eventType": "DecisionTaskStarted",
            "decisionTaskStartedEventAttributes": {
                "identity": "decider_801",
                "scheduledEventId": 10,
            },
            "eventTimestamp": datetime(2013, 3, 21, 19, 17, 50, 953000),
            "eventId": 11,
        },
        {
            "eventTimestamp": datetime(2013, 3, 21, 19, 17, 50, 968000),
            "eventType": "ActivityTaskCompleted",
            "activityTaskCompletedEventAttributes": {
                "startedEventId": 8,
                "result": "22",
                "scheduledEventId": 6,
            },
            "eventId": 12,
        },
        {
            "eventType": "DecisionTaskScheduled",
            "decisionTaskScheduledEventAttributes": {
                "startToCloseTimeout": "60",
                "taskList": {"name": "DefaultTaskList"},
            },
            "eventTimestamp": datetime(2013, 3, 21, 19, 17, 50, 968000),
            "eventId": 13,
        },
        {
            "eventType": "DecisionTaskCompleted",
            "eventTimestamp": datetime(2013, 3, 21, 19, 17, 51, 165000),
            "decisionTaskCompletedEventAttributes": {
                "startedEventId": 11,
                "scheduledEventId": 10,
            },
            "eventId": 14,
        },
        {
            "eventType": "ActivityTaskScheduled",
            "activityTaskScheduledEventAttributes": {
                "input": '{"data": [1, 3, 7, 11]}',
                "activityType": {"version": "1", "name": "Sum"},
                "taskList": {"name": "DefaultTaskList"},
                "heartbeatTimeout": "300",
                "scheduleToStartTimeout": "300",
                "control": "control data",
                "startToCloseTimeout": "300",
                "decisionTaskCompletedEventId": 14,
                "activityId": "Sum2a",
                "scheduleToCloseTimeout": "300",
            },
            "eventTimestamp": datetime(2013, 3, 21, 19, 17, 51, 165000),
            "eventId": 15,
        },
        {
            "eventType": "DecisionTaskStarted",
            "decisionTaskStartedEventAttributes": {
                "identity": "decider_700",
                "scheduledEventId": 13,
            },
            "eventTimestamp": datetime(2013, 3, 21, 19, 17, 51, 199000),
            "eventId": 16,
        },
        {
            "eventType": "ActivityTaskStarted",
            "eventTimestamp": datetime(2013, 3, 21, 19, 17, 51, 220000),
            "activityTaskStartedEventAttributes": {
                "identity": "worker_590",
                "scheduledEventId": 15,
            },
            "eventId": 17,
        },
        {
            "eventTimestamp": datetime(2013, 3, 21, 19, 17, 51, 409000),
            "eventType": "ActivityTaskCompleted",
            "activityTaskCompletedEventAttributes": {
                "startedEventId": 17,
                "result": "22",
                "scheduledEventId": 15,
            },
            "eventId": 18,
        },
        {
            "eventType": "DecisionTaskScheduled",
            "decisionTaskScheduledEventAttributes": {
                "startToCloseTimeout": "60",
                "taskList": {"name": "DefaultTaskList"},
            },
            "eventTimestamp": datetime(2013, 3, 21, 19, 17, 51, 409000),
            "eventId": 19,
        },
        {
            "eventType": "DecisionTaskCompleted",
            "eventTimestamp": datetime(2013, 3, 21, 19, 17, 51, 436000),
            "decisionTaskCompletedEventAttributes": {
                "startedEventId": 16,
                "scheduledEventId": 13,
            },
            "eventId": 20,
        },
        {
            "completeWorkflowExecutionFailedEventAttributes": {
                "cause": "UNHANDLED_DECISION",
                "decisionTaskCompletedEventId": 20,
            },
            "eventType": "CompleteWorkflowExecutionFailed",
            "eventTimestamp": datetime(2013, 3, 21, 19, 17, 51, 436000),
            "eventId": 21,
        },
        {
            "eventType": "DecisionTaskStarted",
            "decisionTaskStartedEventAttributes": {
                "identity": "decider_41",
                "scheduledEventId": 19,
            },
            "eventTimestamp": datetime(2013, 3, 21, 19, 17, 51, 492000),
            "eventId": 22,
        },
    ],
    "workflowType": {"version": "1", "name": "Sum"},
    "previousStartedEventId": 16,
    "startedEventId": 22,
    "workflowExecution": {
        "workflowId": "sum_2113",
        "runId": "12ah+IEeaG98J+2Y/mMPhY98/0POIVMhfin3kFzilMUbQ=",
    },
    "taskToken": "AAAAKgAAAAEAAAAAAAAAAjaHv5Lk1csWNpSpgCC0bOKbWQv8HfmDMCyp6HvCbcrjeH2ao+M+Jz76e+wNukEX6cyLCf+LEBQmUy83b6Abd1HhduEQ/imaw2YftjNt20QtS75QXgPzOIFQ6rh43MKDwBCcnUpttjUzqieva2Y1eEisq4Ax7pZ+ydKmYBFodCvt48BPFD48L7qtmh14rpF2ic8AuNakilIhG3IL5s/UX1gMLre39Rd03UgK+0KuozCIfXwSU+wILRuSOaNB7cHDhiBFg12FSrUFXRHZVZr/qFhGXCEmLNjf/rOpNC1UoZwV",
}
