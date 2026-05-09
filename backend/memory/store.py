from collections import defaultdict, deque
from backend.schemas import ChatMessage


class SessionMemory:
    def __init__(self, max_messages: int = 16) -> None:
        self.max_messages = max_messages
        self._messages: dict[str, deque[ChatMessage]] = defaultdict(lambda: deque(maxlen=max_messages))

    def append(self, session_id: str, role: str, content: str) -> None:
        self._messages[session_id].append(ChatMessage(role=role, content=content))  # type: ignore[arg-type]

    def get(self, session_id: str) -> list[ChatMessage]:
        return list(self._messages[session_id])

    def summarize_context(self, session_id: str) -> str:
        messages = self.get(session_id)
        if not messages:
            return ""
        return "\n".join(f"{message.role}: {message.content}" for message in messages[-8:])


memory = SessionMemory()
