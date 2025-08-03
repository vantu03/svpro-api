
from collections import defaultdict

connected_users = defaultdict(set)
connected_sessions = dict()


def add_session(session):
    if session.user_id is None or session.session_id is None:
        return
    connected_users[session.user_id].add(session)
    connected_sessions[session.session_id] = session

def remove_session(session):
    if session.session_id is None or session.user_id is None:
        return
    session = connected_sessions.pop(session.session_id, None)
    if session:
        connected_users[session.user_id].discard(session)
        if not connected_users[session.user_id]:
            del connected_users[session.user_id]

def get_ws_by_user(user_id: int):
    return connected_users.get(user_id, set())

def find_ws_by_id(session_id: int):
    return connected_sessions.get(session_id)