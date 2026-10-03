from enum import Enum

class CreateResult(Enum):
    CREATED = "CREATED"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    FAILED = "FAILED"
