from copy import deepcopy


DEFAULT_SERVICES = [
    {
        "id": 1,
        "name": "Financial Aid Office",
        "description": "Payments, scholarships, and general financial support questions.",
        "expected_duration": 15,
        "priority": "high",
    },
    {
        "id": 2,
        "name": "Academic Advising",
        "description": "Degree planning, registration help, and academic holds.",
        "expected_duration": 10,
        "priority": "medium",
    },
    {
        "id": 3,
        "name": "IT Help Desk",
        "description": "Password resets, device setup, and campus technology support.",
        "expected_duration": 20,
        "priority": "low",
    },
]

SERVICES = deepcopy(DEFAULT_SERVICES)
QUEUE_ENTRIES = []
QUEUE_HISTORY = []
NOTIFICATIONS = []

NEXT_IDS = {
    "service": 4,
    "queue": 1,
    "notification": 1,
}


def next_id(kind):
    current = NEXT_IDS[kind]
    NEXT_IDS[kind] += 1
    return current


def reset_state():
    SERVICES[:] = deepcopy(DEFAULT_SERVICES)
    QUEUE_ENTRIES.clear()
    QUEUE_HISTORY.clear()
    NOTIFICATIONS.clear()
    NEXT_IDS["service"] = 4
    NEXT_IDS["queue"] = 1
    NEXT_IDS["notification"] = 1
