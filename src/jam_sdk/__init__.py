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

8.12

class MySolver(BaseSolver):
    async def get_quote(self, chain_id: int, request: QuoteRequest) -> QuoteResponse | QuoteError:
        print(f"Getting quote for chain {chain_id} with request: {request}")
        quote_response = QuoteResponse(
            quote_id=request.quote_id,
            amounts=[TokenAmountResponse("0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174", 100000)],
            fee=50000000000000000,
            executor="0x0000000000000000000000000000000000000000",
        )
        print(f"Quote response: {quote_response}")
        return quote_response

    async def execute(self, request: ExecuteRequest, quote_cache: CachedQuote) -> ExecuteResponse | ExecuteError:
        print(f"Executing request: {request}")
        interactions = [InteractionData(result=True, to="0x0000", value=0, data="0x00000000000")]
        account = self.web3.eth.account.from_key("<a private key>")
        settle_tx = await self.build_settle(
            quote_cache.request,
            quote_cache.response,
            interactions,
            request,
            self.jam_contract.address,
            {"from": account.address},
        )
        print(f"Built settlement transaction: {settle_tx}")
        signed_transaction = account.sign_transaction(settle_tx)
        print(f"Signed transaction: {signed_transaction}")
        await self.web3.eth.send_raw_transaction(signed_transaction.rawTransaction)
        print(f"Transaction sent successfully.")
        return ExecuteResponse(request.quote_id)

if __name__ == "__main__":
    connection = SolverConnection(
        "velvet", "041f760e-a2a2-4d1e-a90c-af9642b99498", "wss://api-test.bebop.xyz/jam/ethereum/solver"
    )
    solver = MySolver(chain_id=137, rpc_url="https://polygon-rpc.com", connection=connection)
    print("Solver initialized.")
    asyncio.run(solver.start())
