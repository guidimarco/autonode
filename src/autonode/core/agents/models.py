"""
Agent configuration DTOs (framework-agnostic).

Loaded from YAML/JSON in infrastructure; validated when building the graph.
"""

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class AgentConfig(BaseModel):
    """
    DTO for the agent configuration.
    """

    id: str = Field(..., description="The unique identifier for the agent.")
    name: str | None = Field(None, description="The name of the agent.")
    model: str = Field(..., description="The model to use for the agent.")
    temperature: float = Field(0.0, description="The temperature to use for the agent.")
    tools: list[str] = Field(..., description="The tools to use for the agent.")
    role: str | None = Field(None, description="The role of the agent.")
    system_prompt: str | None = Field(None, description="The system prompt to use for the agent.")

    @field_validator("id", "model")
    @classmethod
    def validate_non_empty_string(cls, v: str, info: ValidationInfo) -> str:
        if not v.strip():
            raise ValueError(
                f"[AgentConfig] The agent needs a non-empty string '{info.field_name}'"
            )
        return v

    @field_validator("name", mode="before")
    @classmethod
    def set_name(cls, v: object, info: ValidationInfo) -> str | None:
        if v is None or (isinstance(v, str) and not v.strip()):
            raw_id = info.data.get("id")
            return None if raw_id is None else str(raw_id)
        if isinstance(v, str):
            return v
        raise TypeError(f"[AgentConfig] name must be str or null, got {type(v).__name__}")

    @field_validator("tools")
    @classmethod
    def validate_tools(cls, v: list[str], info: ValidationInfo) -> list[str]:
        """Validate tool names against the registry when context provides one."""
        registry = info.context.get("tool_registry") if info.context else None
        if registry:
            registry.get_tool_list_strict(v)
        return v
