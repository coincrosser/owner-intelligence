from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from app.models.schemas import Address, ContactPoint


class AddressUpdateProvider(ABC):
    @abstractmethod
    def update(self, addresses: Iterable[Address]) -> list[Address]:
        raise NotImplementedError


class AddressStandardizer(ABC):
    @abstractmethod
    def standardize(self, addresses: Iterable[Address]) -> list[Address]:
        raise NotImplementedError


class AppendVendorClient(ABC):
    @abstractmethod
    def export_payload(self, addresses: Iterable[Address]) -> str:
        raise NotImplementedError

    @abstractmethod
    def import_appends(self, payload: str) -> list[ContactPoint]:
        raise NotImplementedError


class RinglessVoicemailClient(ABC):
    @abstractmethod
    def send(self, owner_id: str, phone: str, message: str) -> str:
        raise NotImplementedError


class SMSClient(ABC):
    @abstractmethod
    def send(self, owner_id: str, phone: str, message: str) -> str:
        raise NotImplementedError


class EmailClient(ABC):
    @abstractmethod
    def send(self, owner_id: str, email: str, message: str) -> str:
        raise NotImplementedError
