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
        print(f"Getting quote for chain {chain_id} with request: {request}")
        sell_token_address = request.sell_tokens[0].address
        sell_token_amount = request.sell_tokens[0].amount
        buy_token_address = request.buy_tokens[0].address

        # Your API call code
        method = "get"
        apiUrl = "https://api.1inch.dev/swap/v5.2/1/quote"
        requestOptions = {
            "headers": {
                "Authorization":os.environ.get("YOUR_1INCH_API_KEY")
            },
            "body": {},
            "params": {
                "src": sell_token_address,
                "dst": buy_token_address,
                "amount": sell_token_amount ,
                "includeTokensInfo": "true",
                "includeProtocols": "true",
                "includeGas": "true"
            }
        }

        # Prepare request components
        headers = requestOptions.get("headers", {})
        body = requestOptions.get("body", {})
        params = requestOptions.get("params", {})

        response = requests.get(apiUrl, headers=headers, params=params)

        # print("hiiiiiiiiiiiiiii I am 1inch api reponse" ,response.json())
        response_data = response.json()
        to_amount = response_data.get('toAmount')
        to_token_address = response_data.get('toToken', {}).get('address')
        gas_fee = response_data.get('gas')

        # Your existing quote response logic
        quote_response = QuoteResponse(
            quote_id=request.quote_id,
            amounts=[TokenAmountResponse(to_token_address, to_amount)],
            fee=gas_fee,
            executor="0x5003F58BE3E0933559E6Ee00EfAb405C0F71E61F",
        )

        print(f"Quote response: {quote_response}")
        
        # Your subsequent API call using quote_id
        quote_id = request.quote_id
       
        url = "https://api-test.bebop.xyz/jam/ethereum/v1/order"
        data = {
            "quote_id": quote_id,
            "signature": "string",
            "sign_scheme": "EIP712"
        }
        response = requests.post(url, json=data, auth=(os.environ.get("USER_ENDPOINT"), os.environ.get("USER_ENDPOINT_AUTHORIZATION")))


        if response.status_code // 100 == 2:
            print("POST request successful")
            print("Response:", response.json())
        else:
            print(f"POST request failed with status code {response.status_code}")
            print("Response:", response.text)

        return quote_response

    
    
    async def execute(self, request: ExecuteRequest, quote_cache: CachedQuote) -> ExecuteResponse | ExecuteError:
        # Your execution logic
        print(f"Executing request: {request}")
        interactions = [InteractionData(result=True, to="0x0000", value=0, data="0x00000000000")]
        account = self.web3.eth.account.from_key(os.environ.get("YOUR_PRIVATE_KEY"))
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
        os.environ.get("SOLVER_NAME"), os.environ.get("SOLVER_AUTHORIZATION"), os.environ.get("SOLVER_ENDPOINT")
    )
    solver = MySolver(chain_id=137, rpc_url="https://polygon-rpc.com", connection=connection)
    print("Solver initialized.")
    asyncio.run(solver.start())


































































































































































































