from __future__ import annotations

import asyncio
import logging
import time
from abc import abstractmethod
from dataclasses import asdict

import orjson
from aiocache import Cache
from eth_typing import HexStr
from eth_utils.address import to_checksum_address
from web3 import AsyncHTTPProvider, AsyncWeb3
from web3.middleware.geth_poa import async_geth_poa_middleware
from web3.types import TxParams, Wei
from websockets.client import WebSocketClientProtocol, connect


from jam_sdk.constants import (
    JAM_SETTLEMENT_ABI,
    JAM_SETTLEMENT_CONTRACT,
    QUOTE_CACHE_TTL,
)
from jam_sdk.solver.types import (
    BaseError,
    BaseMessage,
    CachedQuote,
    ExecuteError,
    ExecuteErrorType,
    ExecuteRequest,
    ExecuteResponse,
    InteractionData,
    QuoteError,
    QuoteErrorType,
    QuoteRequest,
    QuoteResponse,
    SolverConnection,
    SolverData,
)

logging.basicConfig(level=logging.INFO)


class BaseSolver:
    """
    Base Solver class for writing custom solvers. Override the `get_quote` and `execute` functions.
    """

    def __init__(self, chain_id: int, rpc_url: str, connection: SolverConnection) -> None:
        """
        Create an instance of the solver with given paramters

        Args:
            chain_id (int): Chain ID of the chain providing solutions for.
            rpc_url (str): JSON RPC Endpoint for the chain.
            connection (SolverConnection): Connection including the details to the JAM server
        """
        self.connection = connection
        self.logger = logging.getLogger("SolverSDK")
        self.web3 = AsyncWeb3(AsyncHTTPProvider(rpc_url))
        self.web3.middleware_onion.inject(async_geth_poa_middleware, "poa", 0)
        self.chain_id = chain_id
        self.jam_contract = self.web3.eth.contract(
            address=to_checksum_address(JAM_SETTLEMENT_CONTRACT[self.chain_id]),
            abi=JAM_SETTLEMENT_ABI,
        )
        self.quote_cache = Cache(Cache.MEMORY)
        self.ws: WebSocketClientProtocol
 

    async def start(self) -> None:
        """Starts a websocket connection to JAM."""
        headers = {"name": self.connection.name, "authorization": self.connection.auth}
        while True:
            try:
                self.ws = await connect(
                    self.connection.url,
                    extra_headers=headers,
                )
                self.logger.info(f"Solver {self.connection.name} - Successfully connected to JAM")
                await self._handle_ws_message()
            except Exception:
                self.logger.exception("Disconnected from JAM. trying again in 5s")
                await asyncio.sleep(5)

    async def _send_response(self, req_msg: dict, response: BaseMessage) -> None:
        """
        Send a response to JAM.

        Args:
            req_msg (dict): Request
            response (BaseMessage): Response
        """
        ws_message = {
            "chain_id": req_msg["chain_id"],
            "msg_topic": req_msg["msg_topic"],
            "msg_type": "error" if isinstance(response, BaseError) else "response",
            "msg": response.to_ws(),
        }
        self.logger.info(f"Sending msg to JAM: {ws_message}")
        await self.ws.send(orjson.dumps(ws_message))

    async def _handle_quote_request(self, msg: dict) -> None:
        """Handle incoming JAM request

        Args:
            msg (dict): json message
        """
        chain_id = msg["chain_id"]
        request = QuoteRequest.from_ws(msg["msg"])
        try:
            response = await self.get_quote(chain_id, request)
        except Exception:
            self.logger.exception("Failed getting solution")
            response = QuoteError(request.quote_id, QuoteErrorType.Unknown, "failed to get solution")
        # TODO: other sanity checks
        if isinstance(response, QuoteResponse):
            await self.quote_cache.add(
                key=response.quote_id, value=CachedQuote(chain_id, request, response), ttl=QUOTE_CACHE_TTL
            )
        await self._send_response(msg, response)

    async def _handle_execute_request(self, msg: dict) -> None:
        """
        Handle execution request from JAM and forward to implemented function

        Args:
            msg (dict): execution request json

        Raises:
            Exception: If the quote missing
        """
        request = ExecuteRequest.from_ws(msg["msg"])
        try:
            cached_quote = await self.quote_cache.get(request.quote_id)
            if not cached_quote:
                raise Exception("Quote missing from cache")
            # TODO: Check expiry
            response = await self.execute(request, cached_quote)
        except Exception:
            self.logger.exception("Failed to execute solution")
            response = ExecuteError(request.quote_id, ExecuteErrorType.Reject, "failed to execute order")

        self.logger.info(response)
        await self._send_response(msg, response)


    def __init__(self):
        self.msg = None

    async def _handle_ws_message(self) -> None:
        """
        Handle websocket message from JAM
        """
        async for data in self.ws:
            msg = orjson.loads(data)
            if isinstance(msg, dict):
                self.logger.info(f"Solver msg received: {msg}")
                if msg["msg_topic"] == "quote" and msg["msg_type"] == "request":
                    await self._handle_quote_request(msg)
                elif msg["msg_topic"] == "execute_order" and msg["msg_type"] == "request":
                    await self._handle_execute_request(msg)
                else:
                    self.logger.info("Unrecognised message")

    # corresponds to order in `settle` call
    def encode_order(self, order: QuoteRequest, quote_response: QuoteResponse) -> dict:
        """
        Encode a JAM Order into dict ready to submit through settlement.

        Args:
            order (QuoteRequest): The request for this order.
            amounts (list[TokenAmountResponse]): Tokens and amounts given as a response to the JAM order.

        Returns:
            dict: Structured order data ready for submission to settlement.
        """
        buy_tokens: list[str] = []
        sell_tokens: list[str] = []
        buy_amounts: list[int] = []
        sell_amounts: list[int] = []

        for buy_token in order.order_buy_tokens:
            buy_tokens.append(buy_token.address)
            if buy_token.amount:
                buy_amounts.append(buy_token.amount)

        for sell_token in order.order_sell_tokens:
            sell_tokens.append(sell_token.address)
            if sell_token.amount:
                sell_amounts.append(sell_token.amount)

        if len(buy_amounts) == 0:
            buy_amounts += [amount.amount for amount in quote_response.amounts]
        elif len(sell_amounts) == 0:
            sell_amounts += [amount.amount for amount in quote_response.amounts]

        encoded_order = {
            "taker": order.taker,
            "receiver": order.receiver,
            "expiry": order.expiry,
            "nonce": order.nonce,
            "executor": quote_response.executor,
            "minFillPercent": 10000,  # 100%
            "hooksHash": order.hooks_hash,
            "sellTokens": sell_tokens,
            "buyTokens": buy_tokens,
            "sellAmounts": sell_amounts,
            "buyAmounts": buy_amounts,
            "sellNFTIds": [],
            "buyNFTIds": [],
            "sellTokenTransfers": order.sell_token_transfers,
            "buyTokenTransfers": order.buy_token_transfers,
        }

        return encoded_order

    def encode_interactions(self, interactions: list[InteractionData]) -> list[dict]:
        """
        Encode the interactions parameter of a settlement call.

        Args:
            interactions (list[InteractionData]): List of interactions

        Returns:
            list[dict]: Interactions ready for submission to settlement.
        """
        return [asdict(interaction) for interaction in interactions]

    async def build_settle(
        self,
        quote_request: QuoteRequest,
        quote_response: QuoteResponse,
        interactions: list[InteractionData],
        execute_request: ExecuteRequest,
        balance_recipient: str,
        tx_params: TxParams | None = None,
    ) -> TxParams:
        """
        Simulate and build the settlement call to JAM.

        Args:
            quote_request (QuoteRequest): Quote request received for this order
            quote_response (QuoteResponse): Quote response given for this order
            interactions (list[InteractionData]): List of interactions to execute for this order
            execute_request (ExecuteRequest): Execute request received for this order
            balance_recipient (str): The recepient of the user balance before interactions.
            txParams (TxParams | None, optional): _description_. Optional transaction parameters (to, from etc.) to add while building the transaction.

        Raises:
            Exception: Will be raised if the simulating or building fails. This includes gas estimation issues.

        Returns:
            TxParams: Transaction object ready to sign.
        """
        if time.time() > quote_request.expiry:
            raise Exception("Order Expired")
        order = self.encode_order(quote_request, quote_response)
        self.logger.info(f"{order=}")
        taker_permits_info: dict | None = execute_request.get_permits_blockchain_args(quote_request.approval_type)
        if taker_permits_info:
            call_data: HexStr = self.jam_contract.encodeABI(
                fn_name="settleWithPermitsSignatures",
                args=[
                    order,
                    execute_request.signature.to_blockchain_args(),
                    taker_permits_info,
                    self.encode_interactions(interactions),
                    quote_request.hooks.to_blockchain_args(),
                    SolverData(balance_recipient).to_blockchain_args(),
                ],
            )
        else:
            call_data = self.jam_contract.encodeABI(
                fn_name="settle",
                args=[
                    order,
                    execute_request.signature.to_blockchain_args(),
                    self.encode_interactions(interactions),
                    quote_request.hooks.to_blockchain_args(),
                    SolverData(balance_recipient).to_blockchain_args(),
                ],
            )

        base_settle_tx: TxParams = {
            "chainId": self.chain_id,
            "to": self.jam_contract.address,
            "data": call_data,
        }

        settle_tx = base_settle_tx | tx_params if tx_params else base_settle_tx

        try:
            gas = await self.web3.eth.estimate_gas(settle_tx)
        except Exception:
            self.logger.exception(f"build_settle estimation failed for transaction {settle_tx=}")
            raise

        settle_tx_extra: TxParams = {"value": Wei(0), "gas": gas, "chainId": self.chain_id}
        settle_tx = settle_tx | settle_tx_extra
        return settle_tx

    @abstractmethod
    async def get_quote(self, chain_id: int, request: QuoteRequest) -> QuoteResponse | QuoteError:
        """
        Get a solution to the quote request.

        Args:
            chain_id (int): Chain ID
            request (QuoteRequest): Request for quote

        Returns:
            QuoteResponse | QuoteError: Return a `QuoteResponse` with quoted amounts or `QuoteError` to indicate a failure.
        """
        ...

    @abstractmethod
    async def execute(self, request: ExecuteRequest, quote_cache: CachedQuote) -> ExecuteResponse | ExecuteError:
        """
        Execute the given quote.

        Args:
            request (ExecuteRequest): An execution request with quote details and user signatures.
            quote_cache (CachedQuote): Cached quote request and response for the given execution request.

        Returns:
            ExecuteResponse | ExecuteError: An `ExecuteResponse` for a successful execution and `ExecuteError` otherwise
        """
        ...
