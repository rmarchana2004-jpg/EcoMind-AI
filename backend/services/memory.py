conversations = {}


def get_conversation(session_id: str):
    if session_id not in conversations:
        conversations[session_id] = {
            "environment": {},
            "pending_field": None
        }

    return conversations[session_id]


def update_conversation(session_id: str, data: dict):
    conversation = get_conversation(session_id)

    for key, value in data.items():
        if value is not None:
            if key == "pending_field":
                conversation["pending_field"] = value
            else:
                conversation["environment"][key] = value

    return conversation


def get_environment(session_id: str):
    conversation = get_conversation(session_id)
    return conversation.get("environment", {})


def set_pending_field(session_id: str, field: str):
    conversation = get_conversation(session_id)
    conversation["pending_field"] = field


def get_pending_field(session_id: str):
    conversation = get_conversation(session_id)
    return conversation.get("pending_field")


def clear_pending_field(session_id: str):
    conversation = get_conversation(session_id)
    conversation["pending_field"] = None


def clear_conversation(session_id: str):
    if session_id in conversations:
        del conversations[session_id]