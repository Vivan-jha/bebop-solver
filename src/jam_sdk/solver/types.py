from __future__ import annotations

import dataclasses
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, cast

from eth_utils.abi import collapse_if_tuple
from web3.auto import w3

from jam_sdk.constants import HASH_HOOKS_ABI


class ApprovalType(Enum):
    Standard = "Standard"
    Permit = "Permit"
    Permit2 = "Permit2"


class OrderType(Enum):
    OneToOne = "121"
    OneToMany = "12M"
    ManyToOne = "M21"
    ManyToMany = "M2M"


class JamCommand(Enum):
    SIMPLE_TRANSFER = "00"
    PERMIT2_TRANSFER = "01"
    CALL_PERMIT_THEN_TRANSFER = "02"
    CALL_PERMIT2_THEN_TRANSFER = "03"
    NATIVE_TRANSFER = "04"
    NFT_ERC721_TRANSFER = "05"
    NFT_ERC1155_TRANSFER = "06"


class BaseMessage:
    @abstractmethod
    def to_ws(self) -> dict:
        ...

    @staticmethod
    @abstractmethod
    def from_ws(data: dict) -> Any:
        ...


@dataclass
class TokenAmount(BaseMessage):
    address: str
    amount: int | None

    def to_ws(self) -> dict:
        return {
            "address": self.address,
            "amount": str(self.amount) if self.amount else None,
        }

    @staticmethod
    def from_ws(data: dict) -> TokenAmount:
        return TokenAmount(
            address=data["address"],
            amount=(int(data["amount"]) if "amount" in data and data["amount"] is not None else None),
        )


@dataclass
class TokenAmountResponse(TokenAmount):
    amount: int


@dataclass
class InteractionData:
    result: bool
    to: str
    value: int
    data: str

    def to_ws(self) -> dict:
        return {
            "result": self.result,
            "to": self.to,
            "value": str(self.value),
            "data": self.data,
        }

    @staticmethod
    def from_ws(data: dict) -> InteractionData:
        return InteractionData(
            result=data["result"],
            to=data["to"],
            value=int(data["value"]),
            data=data["data"],
        )


@dataclass
class AllHooks:
    before_settle: list[InteractionData]
    after_settle: list[InteractionData]

    def hash_hooks(self) -> str:
        def flatten_hooks(h: InteractionData) -> tuple[bool, str, int, str]:
            return h.result, h.to, h.value, h.data

        if len(self.after_settle) == 0 and len(self.before_settle) == 0:
            return "0x0000000000000000000000000000000000000000000000000000000000000000"

        hooks = [[flatten_hooks(h) for h in self.before_settle], [flatten_hooks(h) for h in self.after_settle]]
        args_types = [collapse_if_tuple(cast(dict[str, Any], arg)) for arg in HASH_HOOKS_ABI["inputs"]]
        hooks_encoded = w3.codec.encode(args_types, [hooks])
        keccak_hash = w3.keccak(primitive=hooks_encoded)
        return keccak_hash.hex()

    def to_blockchain_args(self) -> list[list[dict[str, Any]]]:
        return [
            [interaction.to_ws() for interaction in self.before_settle],
            [interaction.to_ws() for interaction in self.after_settle],
        ]


@dataclass
class InteractionDetails:
    data: InteractionData
    gas: int


@dataclass
class QuoteRequest(BaseMessage):
    order_type: OrderType
    quote_id: str
    base_settle_gas: int
    approval_type: ApprovalType
    taker: str
    receiver: str
    expiry: int
    nonce: int
    hooks: AllHooks
    hooks_hash: str
    sell_tokens: list[TokenAmount]
    buy_tokens: list[TokenAmount]
    sell_token_transfers: str
    buy_token_transfers: str

    def to_ws(self) -> dict:
        data = dataclasses.asdict(self)
        data["order_type"] = self.order_type.value
        data["hooks"] = self.hooks.to_blockchain_args()
        data["approval_type"] = self.approval_type.value
        data["sell_tokens"] = [token.to_ws() for token in self.sell_tokens]
        data["buy_tokens"] = [token.to_ws() for token in self.buy_tokens]
        data["nonce"] = str(self.nonce)
        return data

    @staticmethod
    def from_ws(data: dict) -> QuoteRequest:
        return QuoteRequest(
            order_type=OrderType(data["order_type"]),
            quote_id=data["quote_id"],
            base_settle_gas=data["base_settle_gas"],
            approval_type=ApprovalType(data["approval_type"]),
            taker=data["taker"],
            receiver=data["receiver"],
            expiry=data["expiry"],
            nonce=int(data["nonce"]),
            hooks=AllHooks(
                before_settle=[InteractionData.from_ws(interaction) for interaction in data["hooks"][0]],
                after_settle=[InteractionData.from_ws(interaction) for interaction in data["hooks"][1]],
            ),
            hooks_hash=data["hooks_hash"],
            buy_tokens=[TokenAmount.from_ws(token) for token in data["buy_tokens"]],
            sell_tokens=[TokenAmount.from_ws(token) for token in data["sell_tokens"]],
            sell_token_transfers=data["sell_token_transfers"],
            buy_token_transfers=data["buy_token_transfers"],
        )

    def _merge_tokens(self, tokens: list[TokenAmount]) -> list[TokenAmount]:
        """
        Combine split tokens

        Args:
            tokens (list[TokenAmount]): list of tokens

        Returns:
            _type_: merged tokens
        """
        merged_tokens: dict[str, TokenAmount] = {}
        for token in tokens:
            if token.address in merged_tokens and token.amount:
                current_amount = merged_tokens[token.address].amount
                if current_amount:
                    merged_tokens[token.address].amount = current_amount + token.amount
            else:
                merged_tokens[token.address] = TokenAmount(token.address, token.amount)
        return list(merged_tokens.values())

    @property
    def order_sell_tokens(self) -> list[TokenAmount]:
        """
        tokens formatted as required for the jam order object
        """
        return self._merge_tokens(self.sell_tokens)

    @property
    def order_buy_tokens(self) -> list[TokenAmount]:
        """
        tokens formatted as required for the jam order object
        """
        return self._merge_tokens(self.buy_tokens)

    def decode_sell_token_transfers(self) -> list[JamCommand]:
        return [
            JamCommand(self.sell_token_transfers[i * 2 : i * 2 + 2])
            for i in range(1, int(len(self.sell_token_transfers) / 2))
        ]


@dataclass
class QuoteResponse(BaseMessage):
    quote_id: str  # Quote ID of the request
    amounts: list[TokenAmountResponse]  # Output amounts
    fee: int  # Estimated fee in native token
    executor: str

    def to_ws(self) -> dict:
        return {
            "quote_id": self.quote_id,
            "amounts": [amount.to_ws() for amount in self.amounts],
            "fee": str(self.fee),
            "executor": self.executor,
        }

    @staticmethod
    def from_ws(msg: dict[str, Any]) -> QuoteResponse:
        amounts: list[TokenAmountResponse] = []
        for amount in msg["amounts"]:
            amounts.append(TokenAmountResponse(amount["address"], int(amount["amount"])))

        return QuoteResponse(quote_id=msg["quote_id"], amounts=amounts, fee=int(msg["fee"]), executor=msg["executor"])


class SignatureType(Enum):
    NONE = 0
    EIP712 = 1
    EIP1271 = 2
    ETHSIGN = 3

    @staticmethod
    def from_str(name: str) -> SignatureType:
        return SignatureType[name]

    def to_str(self) -> str:
        return str(self.name)


@dataclass
class Signature(BaseMessage):
    signature_type: SignatureType
    signature_bytes: str

    def to_ws(self) -> dict:
        return {
            "signature_type": self.signature_type.to_str(),
            "signature_bytes": self.signature_bytes,
        }

    @staticmethod
    def from_ws(data: dict) -> Signature:
        return Signature(
            signature_type=SignatureType.from_str(data["signature_type"]),
            signature_bytes=data["signature_bytes"],
        )

    def to_blockchain_args(self) -> dict:
        return {"signatureType": self.signature_type.value, "signatureBytes": self.signature_bytes}


@dataclass(init=True, frozen=True, order=True)
class PermitsInfo:
    signature: str
    deadline: int
    token_addresses: list[str]  # only for Permit2, for Permit it's []
    token_nonces: list[int]  # only for Permit2, for Permit it's []

    def to_ws(self) -> dict:
        return {
            "signature": self.signature,
            "deadline": str(self.deadline),
            "token_addresses": self.token_addresses,
            "token_nonces": [str(nonce) for nonce in self.token_nonces],
        }

    @staticmethod
    def from_ws(data: dict) -> PermitsInfo:
        return PermitsInfo(
            signature=data["signature"],
            deadline=int(data["deadline"]),
            token_addresses=data["token_addresses"],
            token_nonces=[int(nonce) for nonce in data["token_nonces"]],
        )


@dataclass(init=True, frozen=True, order=True)
class SolverData:
    balance_recipient: str
    cur_fill_percent: int = 10000

    def to_blockchain_args(self) -> dict:
        return {"balanceRecipient": self.balance_recipient, "curFillPercent": self.cur_fill_percent}


@dataclass
class ExecuteRequest(BaseMessage):
    quote_id: str
    signature: Signature
    permits_info: PermitsInfo | None = None

    def to_ws(self) -> dict:
        if self.permits_info:
            return {
                "quote_id": self.quote_id,
                "signature": self.signature.to_ws(),
                "permits_info": self.permits_info.to_ws(),
            }
        return {"quote_id": self.quote_id, "signature": self.signature.to_ws()}

    @staticmethod
    def from_ws(data: dict) -> ExecuteRequest:
        if "permits_info" in data:
            return ExecuteRequest(
                quote_id=data["quote_id"],
                signature=Signature.from_ws(data["signature"]),
                permits_info=PermitsInfo.from_ws(data["permits_info"]),
            )
        return ExecuteRequest(quote_id=data["quote_id"], signature=Signature.from_ws(data["signature"]))

    def get_permits_blockchain_args(self, approval_type: ApprovalType) -> dict | None:
        if approval_type == ApprovalType.Permit and self.permits_info:
            return {
                "permitSignatures": [self.permits_info.signature],
                "signatureBytesPermit2": "0x",
                "noncesPermit2": [],
                "deadline": self.permits_info.deadline,
            }
        elif approval_type == ApprovalType.Permit2 and self.permits_info:
            return {
                "permitSignatures": [],
                "signatureBytesPermit2": self.permits_info.signature,
                "noncesPermit2": self.permits_info.token_nonces,
                "deadline": self.permits_info.deadline,
            }
        return None


@dataclass
class ExecuteResponse(BaseMessage):
    quote_id: str

    def to_ws(self) -> dict:
        return {"quote_id": self.quote_id}

    @staticmethod
    def from_ws(data: dict) -> ExecuteResponse:
        return ExecuteResponse(quote_id=data["quote_id"])


class QuoteErrorType(Enum):
    Unavailable = "unavailable"  # Unavailable to provide quotes
    NotSupported = "not_supported"  # Type of order or tokens not supported
    GasExceedsSize = "gas_exceeds_size"  # Order size is too small to cover fee
    Unknown = "unknown"  # Unknown error
    Timeout = "timeout"  # Solver took too long to respond


class ExecuteErrorType(Enum):
    Reject = "reject"  # Rejected executing the order
    Timeout = "timeout"  # Solver took too long to respond


@dataclass
class BaseError(BaseMessage):
    quote_id: str
    error_type: Enum
    error_message: str | None

    def to_ws(self) -> dict:
        return {
            "quote_id": self.quote_id,
            "error_type": self.error_type.value,
            "error_msg": self.error_message,
        }


@dataclass
class QuoteError(BaseError):
    error_type: QuoteErrorType

    @staticmethod
    def from_ws(data: dict) -> QuoteError:
        return QuoteError(data["quote_id"], QuoteErrorType(data["error_type"]), data["error_msg"])


@dataclass
class ExecuteError(BaseError):
    error_type: ExecuteErrorType

    @staticmethod
    def from_ws(data: dict) -> ExecuteError:
        return ExecuteError(data["quote_id"], ExecuteErrorType(data["error_type"]), data["error_msg"])


@dataclass
class CachedQuote:
    chain_id: int
    request: QuoteRequest
    response: QuoteResponse


@dataclass
class SolverConnection:
    name: str
    auth: str
    url: str
