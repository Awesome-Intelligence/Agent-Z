"""Public exception definitions"""


class AgentError(Exception):
    """Base exception"""

    def __init__(self, message: str, code: int = 1000):
        self.message = message
        self.code = code
        super().__init__(self.message)


class BrainServiceError(AgentError):
    """Brain Service error"""

    def __init__(self, message: str, code: int = 2000):
        super().__init__(message, code)


class ExecutorError(AgentError):
    """Executor error"""

    def __init__(self, message: str, code: int = 3000):
        super().__init__(message, code)


class ToolError(AgentError):
    """Tool error"""

    def __init__(self, message: str, tool_name: str = "", code: int = 4000):
        self.tool_name = tool_name
        super().__init__(message, code)


class ValidationError(AgentError):
    """Validation error"""

    def __init__(self, message: str, field: str = "", code: int = 5000):
        self.field = field
        super().__init__(message, code)


class SecurityError(AgentError):
    """Security error"""

    def __init__(self, message: str, code: int = 6000):
        super().__init__(message, code)


class TimeoutError(AgentError):
    """Timeout error"""

    def __init__(self, message: str, timeout: float = 0, code: int = 7000):
        self.timeout = timeout
        super().__init__(message, code)


class InputValidationError(AgentError):
    """Input validation error"""

    def __init__(self, message: str, field: str = "", code: int = 1002):
        self.field = field
        super().__init__(message, code)


class ResponseGenerationError(AgentError):
    """Response generation error"""

    def __init__(self, message: str, code: int = 1003):
        super().__init__(message, code)


class ConfigurationError(AgentError):
    """Configuration error"""

    def __init__(self, message: str, code: int = 1004):
        super().__init__(message, code)


class ToolExecutionError(ToolError):
    """Tool execution error - alias for ToolError for backwards compatibility"""

    def __init__(self, message: str, tool_name: str = "", code: int = 4000):
        super().__init__(message, tool_name, code)
