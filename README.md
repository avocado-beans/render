# Scam-Catcher - Telegram Bot

**Scam-Catcher** is a Telegram bot that listens to every new transaction on either the Binance Smart Chain (BSC) or Ethereum blockchains. It checks whether the transaction is a token creation, and if so, it performs a series of checks to ensure the token is secure and legitimate. If the token passes all security checks, it posts the relevant token details to a designated Telegram channel.

## Features

- **Blockchain Monitoring**: Listens to new transactions on BSC and Ethereum blockchains.
- **Token Creation Detection**: Identifies when a new token is created.
- **Liquidity Pool Check**: Ensures that a liquidity pool worth over $1000 has been created for the token.
- **Liquidity Lock Verification**: Checks whether the liquidity pool for the token is locked.
- **Security Risk Assessment**: Uses the GoPlus Token Security API to check for various security risks such as:
  - Is the token a honeypot?
  - Are there hidden token owners?
  - Are there unreasonable buy/sell fees?
  - And other customizable requirements
- **Customizable Requirements**: Security checks and token requirements can be customized according to user preferences.
- **Automatic Telegram Posting**: Posts the token name, symbol, address, and liquidity pool address to a designated Telegram channel if the token passes all checks.

## How It Works

1. **Listen for Transactions**: The bot listens for every new transaction on the BSC or Ethereum blockchains.
2. **Detect Token Creation**: It checks whether the transaction is related to the creation of a new token.
3. **Liquidity Pool Check**: If the token is newly created, the bot checks whether a liquidity pool worth over $1000 has been created for it.
4. **Liquidity Lock Verification**: It verifies whether the liquidity pool has been locked to prevent rug pulls.
5. **Security Checks**: Using the GoPlus Token Security API, the bot checks for various security risks associated with the token:
   - Is the token a honeypot (i.e., can you sell it)?
   - Are the owner's details hidden?
   - Are the token's buy/sell fees excessively high?
6. **Post to Telegram**: If the token passes all checks, the bot posts the following details to a Telegram channel:
   - Token Name
   - Token Symbol
   - Token Contract Address
   - Liquidity Pool Address

## Installation

1. Clone the repository:

```bash
git clone https://github.com/avocado-beans/scam-catcher.git
```
2. Install requirement packages
```bash
cd scam-catcher
pip install -r requirements.txt
```  
3. Run the bot
```bash
python main.py
```

## This is for fun and educational purposes only!
Please don't buy into any of these coins with any of your real money. They're all probably scams anyway.
   
