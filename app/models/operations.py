from enum import Enum

class OperationType(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    CANCEL = "CANCEL"
