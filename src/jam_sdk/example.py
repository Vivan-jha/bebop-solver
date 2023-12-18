import asyncio

from jam_sdk.solver.base import BaseSolver
from jam_sdk.solver.types import (
    CachedQuote,
    ExecuteError,
    ExecuteRequest,
    ExecuteResponse,
    InteractionData,
    QuoteError,
    QuoteRequest,
    QuoteResponse,
    SolverConnection,
    TokenAmountResponse,
)


class MySolver(BaseSolver):
    async def get_quote(self, chain_id: int, request: QuoteRequest) -> QuoteResponse | QuoteError:
        return QuoteResponse(
            quote_id=request.quote_id,
            amounts=[TokenAmountResponse("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174", 100000)],  # Output token amount
            fee=50000000000000000,  # Fee in wei
            executor="0x0000000000000000000000000000000000000000",
        )

    async def execute(self, request: ExecuteRequest, quote_cache: CachedQuote) -> ExecuteResponse | ExecuteError:
        interactions = [  # A set of calls to make on chain in order to fulfil the quote
            InteractionData(
                result=True, to="0x0000", value=0, data="0x00000000000"  # Whether the interaction must succeed
            )
        ]
        account = self.web3.eth.account.from_key("<a private key>")
        settle_tx = await self.build_settle(
            quote_cache.request,
            quote_cache.response,
            interactions,
            request,
            self.jam_contract.address,  # The recipient of user sell tokens. Can be your own solver contract
            {"from": account.address},
        )
        signed_transaction = account.sign_transaction(settle_tx)
        await self.web3.eth.send_raw_transaction(signed_transaction.rawTransaction)
        return ExecuteResponse(request.quote_id)


if __name__ == "__main__":
    connection = SolverConnection(
        "my-solver", "mypassword123", "wss://api-test.bebop.xyz/jam/polygon/solver"
    )  # Obtain from Bebop
    solver = MySolver(chain_id=137, rpc_url="https://polygon-rpc.com", connection=connection)
    asyncio.run(solver.start())
