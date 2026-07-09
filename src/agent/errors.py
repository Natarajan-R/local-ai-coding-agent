class AgentError(Exception):
    pass

class TransientError(AgentError):
    pass

class SandboxError(AgentError):
    pass

class ToolError(AgentError):
    pass

class ModelError(TransientError):
    pass

