from typing import Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class ValidationError:
    field: str
    message: str
    details: Optional[Dict[str, Any]] = None

class MessageValidationError(Exception):
    def __init__(self, validation_error: ValidationError):
        self.validation_error = validation_error
        super().__init__(f"{validation_error.field}: {validation_error.message}")

def validate_role(role: str) -> None:
    valid_roles = {"user", "assistant", "system"}
    if not role or role.strip() == "":
        raise MessageValidationError(ValidationError("role", "Role cannot be empty"))
    if role not in valid_roles:
        raise MessageValidationError(
            ValidationError("role", f"Invalid role. Must be one of: {', '.join(valid_roles)}")
        )

def validate_content(content: str, max_length: int = 4096) -> None:
    if not content or content.strip() == "":
        raise MessageValidationError(ValidationError("content", "Content cannot be empty"))
    if len(content) > max_length:
        raise MessageValidationError(
            ValidationError(
                "content",
                f"Content exceeds maximum length of {max_length} characters",
                {"current_length": len(content), "max_length": max_length}
            )
        )

def validate_message(role: str, content: str, max_length: int = 4096) -> None:
    validate_role(role)
    validate_content(content, max_length)