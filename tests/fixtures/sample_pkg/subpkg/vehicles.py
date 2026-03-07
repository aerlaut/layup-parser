"""Vehicle class hierarchy — sub-package fixture for cross-module inheritance tests."""

from __future__ import annotations

import abc


class Vehicle(abc.ABC):
    """Abstract base for all vehicles."""

    def __init__(self, make: str, speed: float) -> None:
        self.make: str = make
        self._speed: float = speed

    @abc.abstractmethod
    def move(self) -> str: ...


class Car(Vehicle):
    """A car."""

    def __init__(self, make: str, speed: float, doors: int = 4) -> None:
        super().__init__(make, speed)
        self.doors: int = doors

    def move(self) -> str:
        return f"{self.make} drives at {self._speed} km/h"


class ElectricCar(Car):
    """An electric car — inherits from Car (same module)."""

    def __init__(self, make: str, speed: float, battery_kwh: float) -> None:
        super().__init__(make, speed)
        self.__battery_kwh: float = battery_kwh

    def move(self) -> str:
        return f"{self.make} glides silently at {self._speed} km/h"
