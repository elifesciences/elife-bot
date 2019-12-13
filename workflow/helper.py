from collections import OrderedDict


def define_workflow_step(
        activity_type,
        activity_input,
        activity_id=None,
        version="1",
        control=None,
        heartbeat_timeout=60 * 5,
        schedule_to_close_timeout=60 * 5,
        schedule_to_start_timeout=60 * 5,
        start_to_close_timeout=60 * 5):
    """
    Helper to populate workflow activity definitions
    """
    if not activity_id:
        activity_id = activity_type
    return OrderedDict([
        ("activity_type", activity_type),
        ("activity_id", activity_id),
        ("version", version),
        ("input", activity_input),
        ("control", control),
        ("heartbeat_timeout", heartbeat_timeout),
        ("schedule_to_close_timeout", schedule_to_close_timeout),
        ("schedule_to_start_timeout", schedule_to_start_timeout),
        ("start_to_close_timeout", start_to_close_timeout),
    ])
