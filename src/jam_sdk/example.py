import requests

method = "get"
apiUrl = "https://api.1inch.dev/swap/v5.2/1/quote"
requestOptions = {
      "headers": {
  "Authorization": 'Bearer mjHMxye0xK3h8Zb3zz1iTu4HpKR4Chxy'
},
      "body": {},
      "params": {
  "src": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
  "dst": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
  "amount": "10000000000000000",
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

print(response.json())























# import requests



# url = 'https://api.1inch.dev/swap/v5.2/1/swap'

# # Build the parameters as a dictionary
# params = {
#     'src': '0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee',
#     'dst': '0x111111111117dc0aa78b770fa6a738034120c302',
#     'amount': '10000000000000000',
#     'from':'0xA9560340cA757d537E297c7Cf9416a586D217c07',
#     'slippage':2,
#     'disableEstimate':True,
#     'compatibilityMode':True,
   
# }

# #  'protocols': 'All',
# #     'fee': 0,
# #     'gasPrice': ,
# #     'complexityLevel': 1,
# #     'parts': 1,
# #     'mainRouteParts': 1,
# #     'gasLimit': 100000,


# # Include your API key in the headers
# headers = {
#     'Authorization' : 'Bearer mjHMxye0xK3h8Zb3zz1iTu4HpKR4Chxy',  # Replace with your actual API key
# }

# # Make the GET request with parameters and headers
# response = requests.get(url, params=params, headers=headers)



# # Check if the request was successful (status code 200)
# if response.status_code == 200:
#     try:
#         # Try to decode the JSON content
#         json_response = response.json()
#         print('API Request Response:')
#         print(json_response)
#     except ValueError:
#         print('Invalid JSON content in the response.')
# else:
#     print('API Request Failed. Status Code:', response.status_code)
#     print('Error Details:', response.text)
