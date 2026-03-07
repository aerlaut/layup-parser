"""Animal class hierarchy — used as a fixture for parser tests."""

from __future__ import annotations

import abc
from enum import Enum
from typing import Protocol


class AnimalKind(Enum):
    """Enum of animal categories."""

    MAMMAL = "mammal"
    BIRD = "bird"
    REPTILE = "reptile"


class Flyable(Protocol):
    """Protocol (interface) for things that can fly."""

    def fly(self, altitude: float) -> None: ...


class Animal(abc.ABC):
    """Abstract base class for all animals."""

    _count: int = 0

    def __init__(self, name: str, kind: AnimalKind) -> None:
        self.name: str = name
        self._kind: AnimalKind = kind
        Animal._count += 1

    @abc.abstractmethod
    def speak(self) -> str: ...

    @staticmethod
    def total() -> int:
        return Animal._count

    def describe(self) -> str:
        return f"{self.name} ({self._kind.value})"


class Dog(Animal):
    """A concrete dog."""

    def __init__(self, name: str, breed: str) -> None:
        super().__init__(name, AnimalKind.MAMMAL)
        self.breed: str = breed

    def speak(self) -> str:
        return "Woof!"

    def fetch(self, item: str) -> str:
        return f"{self.name} fetches {item}"


class Parrot(Animal, Flyable):
    """A parrot that can fly."""

    def __init__(self, name: str) -> None:
        super().__init__(name, AnimalKind.BIRD)
        self.__secret: str = "crackers"

    def speak(self) -> str:
        return "Squawk!"

    def fly(self, altitude: float) -> None:
        pass
