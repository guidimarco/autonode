"""
Pydantic schemas for external configuration inputs.

Validation happens at the infrastructure boundary, then data is mapped to pure
core dataclasses via `to_core()`.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from autonode.core.agents.models import AgentModel


class AgentYamlSchema(BaseModel):
    id: str
    name: str | None = None
    model: str
    temperature: float = 0.0
    tools: list[str] = Field(default_factory=list)
    role: str | None = None
    system_prompt: str | None = None

    model_config = ConfigDict(frozen=True)

    @field_validator("id", "model")
    @classmethod
    def _non_empty(cls, value: str, info: ValidationInfo) -> str:
        if not value.strip():
            raise ValueError(f"{info.field_name} must be a non-empty string")
        return value

    @field_validator("tools")
    @classmethod
    def _tools_are_strings(cls, value: list[str]) -> list[str]:
        if any(not isinstance(item, str) for item in value):
            raise ValueError("tools must be a list of strings")
        return [item for item in value if item]

    def to_core(self) -> AgentModel:
        effective_name = self.id if self.name is None or not self.name.strip() else self.name
        return AgentModel(
            id=self.id,
            name=effective_name,
            model=self.model,
            temperature=self.temperature,
            tools=list(self.tools),
            role=self.role,
            system_prompt=self.system_prompt,
        )


class AgentsYamlSchema(BaseModel):
    agents: list[AgentYamlSchema] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True, extra="ignore")

    def to_core(self) -> dict[str, AgentModel]:
        out: dict[str, AgentModel] = {}
        for agent in self.agents:
            core_agent = agent.to_core()
            out[core_agent.id] = core_agent
        return out
