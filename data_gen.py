import uuid
from datetime import datetime, timezone


def _utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _local_now_naive():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f")


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def gen_task_identity(user_id):
    now = _utc_now()
    return {
        "id": f"tid_{uuid.uuid4()}",
        "user_id": user_id,
        "is_demo": False,
        "title": f"e1:Bench task {uuid.uuid4().hex[:8]}",
        "description": "e1:Benchmark test task",
        "local_archived_at": None,
        "utc_created_at": now,
        "utc_updated_at": now,
        "utc_deleted_at": None,
        "sv_utc_uploaded_at": None,
        "cl_needs_upload": True,
        "cl_utc_upload_error_at": None,
    }


def gen_task_schedule(user_id, task_identity_id, group_id=None):
    now = _utc_now()
    return {
        "id": f"tsc_{uuid.uuid4()}",
        "user_id": user_id,
        "task_identity_id": task_identity_id,
        "group_id": group_id,
        "period": "DL",
        "pd_mon": False,
        "pd_tue": False,
        "pd_wed": False,
        "pd_thu": False,
        "pd_fri": False,
        "pd_sat": False,
        "pd_sun": False,
        "duration_type": "DUR",
        "duration_minutes": 30,
        "display_style": "CIRC_F",
        "day_part": "MO",
        "priority": 1,
        "is_optional": False,
        "local_start_date": _today(),
        "local_end_date": None,
        "utc_created_at": now,
        "utc_updated_at": now,
        "utc_deleted_at": None,
        "sv_utc_uploaded_at": None,
        "cl_needs_upload": True,
        "cl_utc_upload_error_at": None,
    }


def gen_timer(user_id, task_identity_id, task_schedule_id, status="RUN"):
    now = _utc_now()
    return {
        "id": f"tmr_{uuid.uuid4()}",
        "user_id": user_id,
        "task_identity_id": task_identity_id,
        "task_schedule_id": task_schedule_id,
        "local_reference_day": _today(),
        "status": status,
        "local_created_at": _local_now_naive(),
        "utc_created_at": now,
        "utc_updated_at": now,
        "utc_deleted_at": None,
        "sv_utc_uploaded_at": None,
        "cl_needs_upload": True,
        "cl_utc_upload_error_at": None,
    }


def gen_group(user_id):
    now = _utc_now()
    return {
        "id": f"grp_{uuid.uuid4()}",
        "user_id": user_id,
        "is_demo": False,
        "title": f"e1:Bench group {uuid.uuid4().hex[:8]}",
        "description": "e1:Benchmark test group",
        "priority": 1,
        "day_part": "MO",
        "separator_seconds": 0,
        "period": "DL",
        "pd_mon": False,
        "pd_tue": False,
        "pd_wed": False,
        "pd_thu": False,
        "pd_fri": False,
        "pd_sat": False,
        "pd_sun": False,
        "is_archived": False,
        "utc_created_at": now,
        "utc_updated_at": now,
        "utc_deleted_at": None,
        "sv_utc_uploaded_at": None,
        "cl_needs_upload": True,
        "cl_utc_upload_error_at": None,
    }
