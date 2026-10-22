"""Common agent machinery: role, permitted tools, prompt, validated structured output."""
from pathlib import Path

from ..models import validate

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"


class ToolNotPermitted(PermissionError):
    pass


class SimulatedFailure(RuntimeError):
    pass


class Agent:
    name = "agent"
    title = "Agent"
    role = ""
    tools = frozenset()          # tools this agent may use; anything else raises
    output_schema = None
    retry_limit = 2

    def __init__(self, ctx):
        self.ctx = ctx           # Newsroom context: db, settings, provider, root, out_dir

    @property
    def prompt(self):
        f = PROMPTS / f"{self.name}.md"
        return f.read_text(encoding="utf-8") if f.is_file() else self.role

    def use(self, tool):
        if tool not in self.tools:
            raise ToolNotPermitted(f"{self.name} may not use {tool}")

    def ask_model(self, payload, task_id=None):
        """Call the configured provider (mock by default). Source text is passed as data only."""
        self.use("llm")
        return self.ctx.provider.complete(self.name, self.prompt, payload, task_id=task_id)

    def run(self, task):
        if task["attempts"] <= int(task["input"].get("_simulate_failures", 0)):  # test hook for failure recovery
            raise SimulatedFailure(f"{self.name}: simulated failure on attempt {task['attempts']}")
        out = self.execute(task)
        if self.output_schema is not None:
            validate(out, self.output_schema, f"{self.name}.output")
        return out

    def execute(self, task):  # pragma: no cover - abstract
        raise NotImplementedError
