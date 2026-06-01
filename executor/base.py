"""
Executor base classes and common definitions
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
import uuid
from common.logging_manager import get_execution_logger


class SafetyLevel(str, Enum):
    """Safety level"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ToolCall(BaseModel):
    """Tool call"""
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    reasoning: Optional[str] = None
    confidence: float = 1.0
    safety_level: SafetyLevel = SafetyLevel.MEDIUM
    execution_id: Optional[str] = None


@dataclass
class ExecutorConfig:
    """Executor configuration"""
    name: str = "BaseExecutor"
    timeout_seconds: float = 30.0
    allowed_commands: List[str] = field(default_factory=list)
    blocked_patterns: List[str] = field(default_factory=list)
    enable_logging: bool = True
    work_dir: Optional[str] = None


class ExecutionResult(BaseModel):
    """Execution result"""
    execution_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: Literal["pending", "success", "error", "timeout"] = "pending"
    tool_call: ToolCall
    output: Optional[str] = None
    error_message: Optional[str] = None
    logs: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    safety_level: SafetyLevel = SafetyLevel.MEDIUM
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class BaseExecutor(ABC):
    """Abstract base class for executor"""
    
    def __init__(self, config: ExecutorConfig):
        self.config = config
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Set up logging"""
        self.logger = get_execution_logger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    async def execute(self, tool_call: ToolCall) -> ExecutionResult:
        """
        Execute tool call
        
        Args:
            tool_call: Tool call request
            
        Returns:
            ExecutionResult: Execution result
        """
        pass
    
    @abstractmethod
    async def validate(self, tool_call: ToolCall) -> tuple[bool, Optional[str]]:
        """
        Validate safety of tool call
        
        Args:
            tool_call: Tool call request
            
        Returns:
            (is_valid, error_message): Whether valid and error message
        """
        pass
    
    def _check_safety(self, command: str) -> tuple[bool, Optional[str]]:
        """Check command safety"""
        if self.config.allowed_commands:
            first_word = command.split()[0] if command.split() else ""
            if first_word not in self.config.allowed_commands:
                return False, f"Command '{first_word}' not in whitelist"
        
        for pattern in self.config.blocked_patterns:
            if pattern in command:
                return False, f"Command contains blocked pattern: {pattern}"
        
        return True, None
    
    async def _log_execution(self, message: str) -> None:
        """Log execution"""
        if self.config.enable_logging:
            self.logger.info(message)