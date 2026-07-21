"""Payment backend protocol."""

from typing import Any, Protocol


class PaymentBackend(Protocol):
    provider: str

    async def create_order(
        self,
        *,
        amount: int,
        currency: str,
        receipt: str,
        notes: dict[str, str] | None = None,
    ) -> dict[str, Any]: ...

    async def verify_payment(self, **payload: Any) -> dict[str, Any]: ...

    def verify_webhook(self, body: bytes, signature: str) -> dict[str, Any]: ...
