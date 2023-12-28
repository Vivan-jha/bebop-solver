import asyncio
import requests
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

import os


class QuoteRequest:
    def __init__(self, quote_id):
        self.quote_id = quote_id

class MySolver(BaseSolver):
    async def get_quote(self, chain_id: int, request: QuoteRequest) -> QuoteResponse | QuoteError:
        print(f"sell token{request.sell_tokens}")
        print(f"Getting quote for chain {chain_id} with request: {request}")
        quote_response = QuoteResponse(
            quote_id=request.quote_id,
            amounts=[TokenAmountResponse("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", 1000000000000000000)],
            fee=100,
            executor="0x5003F58BE3E0933559E6Ee00EfAb405C0F71E61F",
        )

        print(f"Quote response: {quote_response}")
        username ='integrator'
        password ='BWAqTtJmGRh9L2r66DUT'

        # Now, use the obtained quote_id for the subsequent API call
        dynamic_key1 = request.quote_id


        url = "https://api-test.bebop.xyz/jam/ethereum/v1/order"



        data = {
          "quote_id": dynamic_key1,
          "sign_scheme": "EIP712"
        }

        response = requests.post(url, json=data,auth=(username, password))

        if response.status_code // 100 == 2:
            print("POST request successful")
            print("Response:", response.json())
        else:
            print(f"POST request failed with status code {response.status_code}")
            print("Response:", response.text)

        return quote_response

    private_key = os.environ.get("YOUR_PRIVATE_KEY")
    async def execute(self, request: ExecuteRequest, quote_cache: CachedQuote) -> ExecuteResponse | ExecuteError:
        print(f"Executing request: {request}")
        interactions = [InteractionData(result=True, to="0x0000", value=0, data="0x00000000000")]
        account = self.web3.eth.account.from_key("YOUR_PRIVATE_KEY")
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





































































# import asyncio
# from jam_sdk.solver.base import BaseSolver
# from jam_sdk.solver.types import (
#     CachedQuote,
#     ExecuteError,
#     ExecuteRequest,
#     ExecuteResponse,
#     InteractionData,
#     QuoteError,
#     QuoteRequest,
#     QuoteResponse,
#     SolverConnection,
#     TokenAmountResponse,
# )

# import os

# class MySolver(BaseSolver):
#     async def get_quote(self, chain_id: int, request: QuoteRequest) -> QuoteResponse | QuoteError:
#         print(f"sell token{request.sell_tokens}")
#         print(f"Getting quote for chain {chain_id} with request: {request}")
#         quote_response = QuoteResponse(
#             quote_id=request.quote_id,
#             amounts=[TokenAmountResponse("0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", 1000000000000000000)],
#             fee=100,
#             executor="0x5003F58BE3E0933559E6Ee00EfAb405C0F71E61F",
#         )

#         print(f"Quote response: {quote_response}")
#         return quote_response


    
#     private_key = os.environ.get("YOUR_PRIVATE_KEY")
#     async def execute(self, request: ExecuteRequest, quote_cache: CachedQuote) -> ExecuteResponse | ExecuteError:
        
#         print(f"Executing request: {request}")
#         interactions = [InteractionData(result=True, to="0x0000", value=0, data="0x00000000000")]
#         account = self.web3.eth.account.from_key("YOUR_PRIVATE_KEY")
#         settle_tx = await self.build_settle(
#             quote_cache.request,
#             quote_cache.response,
#             interactions,
#             request,
#             self.jam_contract.address,
#             {"from": account.address},
#         )
#         print(f"Built settlement transaction: {settle_tx}")
#         signed_transaction = account.sign_transaction(settle_tx)
#         print(f"Signed transaction: {signed_transaction}")
#         await self.web3.eth.send_raw_transaction(signed_transaction.rawTransaction)
#         print(f"Transaction sent successfully.")
#         return ExecuteResponse(request.quote_id)

# if __name__ == "__main__":
#     connection = SolverConnection(
#         "velvet", "041f760e-a2a2-4d1e-a90c-af9642b99498", "wss://api-test.bebop.xyz/jam/ethereum/solver"
#     )
#     solver = MySolver(chain_id=137, rpc_url="https://polygon-rpc.com", connection=connection)
#     print("Solver initialized.")
#     asyncio.run(solver.start())
