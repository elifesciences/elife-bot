from datetime import datetime

EXPECTED = {
    "executionInfos": [
        {
            "cancelRequested": False,
            "execution": {
                "runId": "12LwsAjESX4JPPUiC7kivsiCCZyxSUroB6oGMxQQG2iXA=",
                "workflowId": "DepositCrossref",
            },
            "executionStatus": "OPEN",
            "startTimestamp": datetime(2013, 6, 17, 15, 39, 33, 464000),
            "workflowType": {"name": "DepositCrossref", "version": "1"},
        }
    ]
}
