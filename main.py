from fastapi import FastAPI, Request
from web3 import Web3
import os, traceback
import threading
import telegram
import requests
import asyncio
import time

chain = 'ethereum'
chat_id = '-1002184767994'
scannerkey = os.environ['ETHCHAINAPI']
provider_url = f"https://mainnet.infura.io/v3/{os.environ['INFURAKEY']}"
abi = [{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"}]

blockspermin = 20
minutes = 5
back_stretch_minutes = 60
width = minutes*blockspermin
back_stretch = back_stretch_minutes*blockspermin

tokens = []
def latest_eth_price():
    url = 'https://api.etherscan.io/api/'
    params = {
	'module': 'stats',
	'action': 'ethprice',
	'apikey': scannerkey,
    }
    response = requests.get(url, params=params)
    return float(response.json()['result']['ethusd'])

def msg_construct(token_address, pair_address, price):
    token_addressHL = f"https://etherscan.io/token/{token_address}"
    lp_addressHL = f"https://etherscan.io/token/{pair_address}"
    cmcHL = f"https://coinmarketcap.com/dexscan/{chain}/{pair_address}"
    price = str(round(float(price[:price.index('e')]), 4)) + price[price.index('e'):]
    price = '$'+price.replace('.', '\\.').replace('e', ' x 10^').replace('-0', '-').replace('-', '\\-')

    text = f"Current Price: [{price}]({cmcHL})\nToken Address: [{token_address}]({token_addressHL})\nLP Address: [{pair_address}]({lp_addressHL})\n"
    return text

def locked(pair_address, from_block):
    filter_params = {
	'fromBlock': from_block,
	'toBlock': w3.eth.block_number,
	'address': Web3.to_checksum_address(pair_address),
	'topics': [TRANSFER_EVENT_SIGNATURE]
    }
    logs = w3.eth.get_logs(filter_params)

    burner = '0x000000000000000000000000000000000000dead'
    uncx = '0x663a5c229c09b049e36dcc11a9b0d4a8eb9db214'
    teamfinance = '0xe2fe530c047f2d85298b07d9333c05737f1435fb'
    pinklock = '0x71b5759d73262fbb223956913ecf4ecc51057641'
    lockers = [uncx, teamfinance, pinklock]

    logs = logs[:100]
    for log in logs:
        sender_address = str(w3.to_hex(log['topics'][1]))
        recipient_address = str(w3.to_hex(log['topics'][2]))

        for address in [sender_address, recipient_address]:
            address = f'0x{address[26:]}'
            if address in lockers:
                return True
    return False

def get_abi(token_address):
    url = 'https://api.etherscan.io/api/'
    params = {
	'module': 'contract',
	'action': 'getabi',
	'address': Web3.to_checksum_address(token_address),
	'apikey': scannerkey,
    }
    return requests.get(url, params=params).json()['result']

def get_balance(wallet_address, token_address):
    url = 'https://api.etherscan.io/api/'
    params = {
	'module': 'account',
	'action': 'tokenbalance',
	'contractaddress': token_address,
	'address': Web3.to_checksum_address(wallet_address),
	'tag': 'latest',
	'apikey': scannerkey,
    }
    balance = requests.get(url, params=params).json()['result']
    try:
        abi = get_abi(token_address)
        token = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=abi) # declaring the token contract
        try:
            decimals = int(token.functions.decimals().call())
        except:
            decimals = 18

        return float(balance)/(10**decimals)
    except:
        return -1

def latest_token_price(token_address, counter_address, pair_address):
    token_balance = get_balance(pair_address, token_address)
    if token_balance > 0 and counter_address.lower() == '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2':
        counter_balance = get_balance(pair_address, counter_address)
        price = (counter_balance*latest_eth_price())/token_balance
        return price
    return 0

async def search_for_creations():
    global w3
    global TRANSFER_EVENT_SIGNATURE
    global CREATION_EVENT_SIGNATURE
    w3 = Web3(Web3.HTTPProvider(provider_url, request_kwargs={'timeout': 60}))
    TRANSFER_EVENT_SIGNATURE = w3.keccak(text='Transfer(address,address,uint256)').hex()
    CREATION_EVENT_SIGNATURE = w3.keccak(text='PairCreated(address,address,address,uint256)').hex()

    bot = telegram.Bot(os.environ['TELEBOTAPI'])
    await bot.sendMessage(chat_id=chat_id, text=f"Codebase Modified\nRebooted to Apply Updates")
    time.sleep(10)
    await bot.sendMessage(chat_id=chat_id, text=f"Target Chain: {chain.upper()}")
    time.sleep(2)
    await bot.sendMessage(chat_id=chat_id, text="Bravo Six, Going Dark")
    print("Bravo Six, Going Dark")

    while True:
        p_start = time.time()
        latest_block = w3.eth.block_number
        print(f'Took {latest_block} as latest block')
        from_block = latest_block - (back_stretch - width)
        to_block = latest_block - (back_stretch - 2*width)
        print(f'Parsing logs from {from_block} to {to_block}')

        temp_tokens = []
        filter_params = {
    	'fromBlock': from_block,
    	'toBlock': to_block,
    	'topics': [CREATION_EVENT_SIGNATURE]}
        logs = w3.eth.get_logs(filter_params)
        for log in logs:
            token_address =  Web3.to_checksum_address(f"0x{str(w3.to_hex(log['topics'][1]))[26:]}")
            counter_address = Web3.to_checksum_address(f"0x{str(w3.to_hex(log['topics'][2]))[26:]}")
            pair_address = Web3.to_checksum_address(f"0x{str(w3.to_hex(log['data']))[26:66]}")
            contract = w3.eth.contract(token_address , abi = abi)
            token_name = contract.functions.name().call()
            token_symbol = contract.functions.symbol().call()
            temp_tokens.append(token_address)
            if token_address in tokens:
                continue
            price = latest_token_price(token_address, counter_address, pair_address)
            if price > 0:
                print(f'Name: {token_name}')
                print(f'Symbol: {token_symbol}')
                print(pair_address)
                price = str("{:e}".format(price))
                is_locked = locked(pair_address, int(log['blockNumber']))
                message = msg_construct(token_address, pair_address, price)
                text = f"🟢 LIQUIDITY LOCKED 🟢\n\nSymbol: {token_symbol}\n{message}" if (is_locked) else f"⚠ LIQUIDITY NOT LOCKED ⚠\n\nSymbol: {token_symbol}\n{message}"
                print(text)
                send_message = (await bot.sendMessage(chat_id=chat_id, text=text, parse_mode = 'MarkdownV2')) if (is_locked) else False
		    
        for token in tokens:
            if (len(tokens)>0) and (not token in temp_tokens):
                tokens.remove(token)
        tokens.extend(temp_tokens)
	    
        absence = time.time()-p_start
        print(f'Finished search round in {round(absence)} seconds.')
        knockout = 180
        if knockout - absence > 0:
            print(f'Taking a well deserved {round((knockout - absence)/60)}-minute break...')
            time.sleep(knockout - absence)

def main():
    while True:
        try:
            asyncio.run(search_for_creations())
        except:
            print(traceback.format_exc())
            time.sleep(60)
		
mainthread = threading.Thread(target=main,)
mainthread.start()

app = FastAPI()
@app.get("/")
async def confirm(request: Request):
    return """My process is purely logistical, narrowly focused by design. I’m not here to take sides. It’s not my place to formulate any opinion. No one who can afford me needs to waste time winning me to some cause."""
