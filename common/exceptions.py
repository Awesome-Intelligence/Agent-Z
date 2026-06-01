"""Public exception definitions"""


class HandsomeAgentError(Exception):
    """Base exception"""
    
    def __init__(self, message: str, code: int = 1000):
        self.message = message
        self.code = code
        super().__init__(self.message)


class BrainServiceError(HandsomeAgentError):
    """Brain Service error"""
    
    def __init__(self, message: str, code: int = 2000):
        super().__init__(message, code)


class ExecutorError(HandsomeAgentError):
    """Executor error"""
    
    def __init__(self, message: str, code: int = 3000):
        super().__init__(message, code)


class ToolError(HandsomeAgentError):
    """Tool error"""
    
    def __init__(self, message: str, tool_name: str = "", code: int = 4000):
        self.tool_name = tool_name
        super().__init__(message, code)


class ValidationError(HandsomeAgentError):
    """Validation error"""
    
    def __init__(self, message: str, field: str = "", code: int = 5000):
        self.field = field
        super().__init__(message, code)


class SecurityError(HandsomeAgentError):
    """Security error"""
    
    def __init__(self, message: str, code: int = 6000):
        super().__init__(message, code)


class TimeoutError(HandsomeAgentError):
    """Timeout error"""

    def __init__(self, message: str, timeout: float = 0, code: int = 7000):
        self.timeout = timeout
        super().__init__(message, code)


class AgentError(HandsomeAgentError):
    """Agent error"""

    def __init__(self, message: str, code: int = 1001):
        super().__init__(message, code)


class InputValidationError(HandsomeAgentError):
    """Input validation error"""

    def __init__(self, message: str, field: str = "", code: int = 1002):
        self.field = field
        super().__init__(message, code)


class ResponseGenerationError(HandsomeAgentError):
    """Response generation error"""

    def __init__(self, message: str, code: int = 1003):
        super().__init__(message, code)


class ConfigurationError(HandsomeAgentError):
    """Configuration error"""

    def __init__(self, message: str, code: int = 1004):
        super().__init__(message, code)


class ToolExecutionError(ToolError):
    """Tool execution error - alias for ToolError for backwards compatibility"""
    
    def __init__(self, message: str, tool_name: str = "", code: int = 4000):
        super().__init__(message, tool_name, code)