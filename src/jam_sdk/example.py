import requests

url = 'https://api.1inch.io/v5.2/1/quote'
src_address = '0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'
dst_address = '0x111111111117dc0aa78b770fa6a738034120c302'
amount = '10000000000000000'

# Build the parameters as a string and concatenate to the URL
params_string = f'src={src_address}&dst={dst_address}&amount={amount}'
full_url = f'{url}?{params_string}'

# Make the GET request with the full URL
response = requests.get(full_url)

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
