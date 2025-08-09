from __future__ import annotations

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import json


class Project(BaseModel):
    id: int | None = Field(default=None)
    name: str
    description: Optional[str] = None
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "Project":
        return cls(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            created_at=row.get("created_at") if hasattr(row, "get") else row["created_at"],
        )


class ProjectFile(BaseModel):
    id: int | None = Field(default=None)
    project_id: int
    filename: str
    path: str
    content_type: Optional[str] = None
    size: Optional[int] = None
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "ProjectFile":
        return cls(
            id=row["id"],
            project_id=row["project_id"],
            filename=row["filename"],
            path=row["path"],
            content_type=row["content_type"],
            size=row["size"],
            created_at=row.get("created_at") if hasattr(row, "get") else row["created_at"],
        )


class ChatSession(BaseModel):
    id: int | None = Field(default=None)
    session_id: str
    title: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "ChatSession":
        return cls(
            id=row["id"],
            session_id=row["session_id"],
            title=row["title"],
            created_at=row.get("created_at") if hasattr(row, "get") else row["created_at"],
            updated_at=row.get("updated_at") if hasattr(row, "get") else row["updated_at"],
        )


class ChatMessage(BaseModel):
    id: int | None = Field(default=None)
    session_id: str
    role: str  # 'user', 'assistant', 'system'
    content: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "ChatMessage":
        metadata = None
        if row["metadata"]:
            try:
                metadata = json.loads(row["metadata"])
            except (json.JSONDecodeError, TypeError):
                metadata = None

        return cls(
            id=row["id"],
            session_id=row["session_id"],
            role=row["role"],
            content=row["content"],
            metadata=metadata,
            created_at=row.get("created_at") if hasattr(row, "get") else row["created_at"],
        )


class ProjectArtifact(BaseModel):
    id: int | None = Field(default=None)
    session_id: str
    artifact_type: str  # 'project_idea', 'tech_stack', 'submission_summary'
    content: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_row(cls, row) -> "ProjectArtifact":
        metadata = None
        if row["metadata"]:
            try:
                metadata = json.loads(row["metadata"])
            except (json.JSONDecodeError, TypeError):
                metadata = None

        return cls(
            id=row["id"],
            session_id=row["session_id"],
            artifact_type=row["artifact_type"],
            content=row["content"],
            metadata=metadata,
            created_at=row.get("created_at") if hasattr(row, "get") else row["created_at"],
            updated_at=row.get("updated_at") if hasattr(row, "get") else row["updated_at"],
        )


