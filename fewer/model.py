"""Shared shapes. Every module speaks in these, nothing else."""
from dataclasses import dataclass, field


@dataclass
class Turn:
    """One stretch where an agent was working, or a human was reading/typing."""
    session: str          # agent/session id
    kind: str             # "agent" (working) | "human" (reading or typing)
    start: float          # unix seconds
    end: float


@dataclass
class Timeline:
    turns: list = field(default_factory=list)   # list[Turn], sorted by start
