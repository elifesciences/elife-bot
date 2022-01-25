from datetime import datetime


EXPECTED = {
    "events": [
        {
            "eventTimestamp": datetime(2013, 3, 21, 19, 17, 50, 379000),
            "eventType": "WorkflowExecutionStarted",
            "workflowExecutionStartedEventAttributes": {
                "childPolicy": "TERMINATE",
                "taskList": {"name": "DefaultTaskList"},
                "workflowType": {"version": "1", "name": "Ping"},
                "executionStartToCloseTimeout": "300",
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
    ],
    "workflowType": {"version": "1", "name": "Ping"},
    "previousStartedEventId": 16,
    "startedEventId": 22,
    "workflowExecution": {
        "workflowId": "cron_FiveMinute",
        "runId": "12ah+IEeaG98J+2Y/mMPhY98/0POIVMhfin3kFzilMUbQ=",
    },
    "taskToken": "AAAAKgAAAAEAAAAAAAAAAjaHv5Lk1csWNpSpgCC0bOKbWQv8HfmDMCyp6HvCbcrjeH2ao+M+Jz76e+wNukEX6cyLCf+LEBQmUy83b6Abd1HhduEQ/imaw2YftjNt20QtS75QXgPzOIFQ6rh43MKDwBCcnUpttjUzqieva2Y1eEisq4Ax7pZ+ydKmYBFodCvt48BPFD48L7qtmh14rpF2ic8AuNakilIhG3IL5s/UX1gMLre39Rd03UgK+0KuozCIfXwSU+wILRuSOaNB7cHDhiBFg12FSrUFXRHZVZr/qFhGXCEmLNjf/rOpNC1UoZwV",
}
