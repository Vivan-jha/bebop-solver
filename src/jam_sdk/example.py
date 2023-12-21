import requests

url = 'https://api.1inch.io/v5.2/1/quote'


# Build the parameters as a dictionary
params = {
    'src': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
    'dst': '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
    'amount': '10000000000000000',
    'protocols': 'All',
    'fee': 0,
    'gasPrice': 'fast',
    'complexityLevel': 1,
    'parts': 1,
    'mainRouteParts': 1,
    'gasLimit': 100000,
    'includeTokensInfo': True,
    'includeProtocols': True,
    'includeGas': True,
}


# Make the GET request with parameters directly
response = requests.get(url, params=params)

# Print the entire response content, including headers
print('Response Content:', response.text)
print('Response Headers:', response.headers)
print('Status Code:', response.status_code)

# Check if the request was successful (status code 200)
if response.status_code == 200:
    try:
        # Try to decode the JSON content
        json_response = response.json()
        print('API Request Response:')
        print(json_response)
    except ValueError:
        print('Invalid JSON content in the response.')
else:
    print('API Request Failed. Status Code:', response.status_code)
    print('Error Details:', response.text)
