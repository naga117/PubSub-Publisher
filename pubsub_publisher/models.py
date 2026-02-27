from dataclasses import dataclass


@dataclass
class LogEntry:
    timestamp: str
    status: str
    message_id: str
    error: str
