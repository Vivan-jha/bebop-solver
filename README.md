# Bebop JAM SDK

![Alt text](../bebop.gif?raw=true "Title")

Official SDK for Bebop JAM.

## Functionality

Supplies an interface to implement providing solutions for Jam:

- Managed websocket connection to JAM
- Simple base class to implement for providing solutions
- Cache management and validation
- Fully typed request and responses
- Jam contract deployments and ABIs

## Getting Started

In order to connect to the JAM server, you will need some authentication details: `host, post, name, authentication`. Please contact a team member to obtain these.

Bebop orders go through 2 stages. Quote & Order.

1. Quote: Given the requested tokens, provide a quote.
2. Execute: Execute on chain the quote previously given. 

To implement these functions, simply implement the `BaseSolver` class with `get_quote` and `execute` functions.

[See example here.](./src/jam_sdk/example.py)