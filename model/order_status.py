from enum import Enum


class OrderStatus(Enum):
    RESERVED  = "RESERVED"
    REJECTED  = "REJECTED"
    PRODUCING = "PRODUCING"
    CONFIRMED = "CONFIRMED"
    RELEASE   = "RELEASE"
