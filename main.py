from fastapi import FastAPI, Request
from web3 import Web3
import threading
import requests
import telegram
import asyncio
import time
import os


wbnb_address = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
bscusd_address = '0xdac17f958d2ee523a2206206994597c13d831ec7'
provider_url = 'https://eth-pokt.nodies.app'
bscscan_api = 'https://api.etherscan.io/api/'
bscscan_api_key = os.environ['ETHCHAINAPI']
bnbprice = 'ethprice'
chain = 'ethereum'
chain = 'bsc'

if chain == 'bsc':
    wbnb_address = '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c'
    bscusd_address = '0x55d398326f99059ff775485246999027b3197955'
    provider_url = 'https://bsc-pokt.nodies.app'
    bscscan_api = 'https://api.bscscan.com/api/'
    bscscan_api_key = os.environ['BSCCHAINAPI']
    bnbprice = 'bnbprice'

w3 = Web3(Web3.HTTPProvider(provider_url))
print(w3.is_connected())
TRANSFER_EVENT_SIGNATURE = w3.keccak(text='Transfer(address,address,uint256)').hex()

back_stretch = 1200
front_limit = 0
minutes = back_stretch / 20

def get_image_url(lp_address):
    url = f'https://coinmarketcap.com/dexscan/{chain}/{lp_address}/'
    try:
        response = requests.get(url)
        img = response.text.split('class="dex-pairs-name"><img class="token-icon" src="')[1].split('" width="')[0]
    except:
        img = 'https://s2.coinmarketcap.com/static/cloud/img/dex/default-icon-day-v3.svg'
    return img

def latest_bnb_price():
    url = bscscan_api
    params = {
	'module': 'stats',
	'action': bnbprice,
	'apikey': bscscan_api_key,
    }
    response = requests.get(url, params=params)
    return float(response.json()['result']['ethusd'])

def get_creator_address(token_address):
    url = bscscan_api
    params = {
	'module': 'contract',
	'action': 'getcontractcreation',
	'contractaddresses': Web3.to_checksum_address(token_address),
	'apikey': bscscan_api_key,
    }

    response = requests.get(url, params=params)
    print(response.json()['result'][0]['contractCreator'])
    return response.json()['result'][0]['contractCreator']

def is_creation_tx(token_address, tx_info):
    is_creation = True if (get_creation_tx_hash(token_address) == tx_info[1]) else False
    return is_creation

def get_creation_tx_hash(token_address):
    url = bscscan_api
    params = {
	'module': 'contract',
	'action': 'getcontractcreation',
	'contractaddresses': Web3.to_checksum_address(token_address),
	'apikey': bscscan_api_key,
    }
    response = requests.get(url, params=params)
    return response.json()['result'][0]['txHash']

def address_type(wallet_address):
    code = str(w3.to_hex(w3.eth.get_code(Web3.to_checksum_address(wallet_address))))
    if len(code) > 3:
        return({'address_type': 'contract_address'})
    elif len(code) <= 3:
        return({'address_type': 'externally_owned_address'})

def get_abi(token_address):
    url = bscscan_api
    params = {
	'module': 'contract',
	'action': 'getabi',
	'address': Web3.to_checksum_address(token_address),
	'apikey': bscscan_api_key,
    }
    return requests.get(url, params=params).json()['result']

def get_balance(wallet_address, token_address):
    url = bscscan_api
    params = {
	'module': 'account',
	'action': 'tokenbalance',
	'contractaddress': token_address,
	'address': Web3.to_checksum_address(wallet_address),
	'tag': 'latest',
	'apikey': bscscan_api_key,
    }
    balance = requests.get(url, params=params).json()['result']
    try:
        abi = get_abi(token_address)
        token = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=abi) # declaring the token contract
        try:
            decimals = int(token.functions.decimals().call())
        except:
            decimals = 18

        return int(balance)/(10**decimals)

    except:
        return -1

def is_null(address, anchor):
    if (len(address.replace(anchor, '')) == address.replace(anchor, '').count('0')):
        return True
    return False

def get_contract_wallet_txns(token_address, latest_block):
    filter_params = {
	'fromBlock': latest_block - back_stretch,
	'toBlock': latest_block,
	'address': Web3.to_checksum_address(token_address),
	'topics': [TRANSFER_EVENT_SIGNATURE]
    }

    logs = w3.eth.get_logs(filter_params)
    balance_book = []
    accounts = []
    total_no_of_logs = len(logs)-1
    print(f'suspect ({token_address}) has had {total_no_of_logs} events since creation')
    if len(logs) > 100:
        logs = logs[-100:]
        print('minimized')

    start = time.time()
    null_interactions = 0
    for log in logs:
        sender_address = str(w3.to_hex(log['topics'][1]))
        recipient_address = str(w3.to_hex(log['topics'][2]))
        null_state_sender = is_null(sender_address, 'x')
        null_state_recipient = is_null(recipient_address, 'x')
        if null_state_sender is False \
            and null_state_recipient is False:
            for address in [sender_address, recipient_address]:
                address = f'0x{address[26:]}'
                if (not address in accounts) and (address_type(address)['address_type'] == 'contract_address'):
                    accounts.append(address)
                    wbnb_balance = get_balance(address, wbnb_address)
                    usd_balance = get_balance(address, bscusd_address)
                    token_balance = get_balance(address, token_address)

                    if ((wbnb_balance > 1 and usd_balance == 0.0) or (usd_balance > 1000 and wbnb_balance == 0.0)) and (token_balance > 1):
                        image_url = get_image_url(address)
                        if ('png' in image_url):
                            print('audited one possible LP')
                            if (wbnb_balance > 1):
                                relative_token_price = (wbnb_balance*latest_bnb_price())/token_balance
                            if (usd_balance > 1):
                                relative_token_price = usd_balance/token_balance

                            response ={
                                f'contract_wallet_address': address,
                                f'relative_token_price': f'${relative_token_price}',
                                f'token_balance': token_balance,
                                f'wbnb_balance': wbnb_balance,
                                f'bsc-usd_balance': usd_balance,
                                f'image_url': image_url
                                }

                            balance_book.append(response)

    if len(balance_book) > 0:
        print(f'Found {len(balance_book)} potential LPs for the token: {token_address}')
    print(f'finished in {round(time.time()-start)} seconds')
    return(balance_book)

async def func():
    bot = telegram.Bot(os.environ['TELEBOTAPI'])
    await bot.sendMessage(chat_id='@th3k1ll3r', text="bravo 6, going dark")
    print("bravo 6, going dark")
    async with bot:
        while True:
            p_start = time.time()
            latest_block = w3.eth.block_number
            print('\n***************************************')
            print(f'checking what happened {back_stretch} blocks (~{back_stretch/1200}hrs) ago on {chain.upper()}...')
            no_of_chunks = round(minutes/5)

            for i in range(no_of_chunks):
                print(f'parsing chunk {i+1}: { latest_block - (back_stretch - 100*i)} to {latest_block - (back_stretch - 100*(i+1))}')
                filter_params = {
        	    'fromBlock': latest_block - (back_stretch - 100*i),
            	    'toBlock': latest_block - (back_stretch - 100*(i+1)),
                    'topics': [TRANSFER_EVENT_SIGNATURE]
                }
                logs = w3.eth.get_logs(filter_params)
                print('finished parsing chunk')
                if i == 0:
                    t_logs = logs
                elif i > 0:
                    t_logs += logs

            creations = {}
            print(f'Done parsing logs ({len(logs)}). now analyzing...')
            tokens = []
            for log in t_logs:
                try:
                    value = int.from_bytes(log['data'], byteorder='big') / 10**18
                    zeroes = str(value).replace('.','').count('0')
                    sender_address = str(w3.to_hex(log['topics'][1]))
                    recipient_address = str(w3.to_hex(log['topics'][2]))

                    if is_null(sender_address, 'x') is True \
                        and is_null(recipient_address, 'x') is False \
                        and value >= 10**6 \
                        and not log['address'] in tokens:
                        if recipient_address[:26] == '0x000000000000000000000000' and len(recipient_address) > 60:
                            recipient_address = f'0x{recipient_address[26:]}'

                        creations.update({f"{log['address']}": [int(log['blockNumber']), log['transactionHash'].hex()]})
                        tokens.append(log['address'])
                        #print(log)
                except:
                    pass

            print(f'created ledger ({len(creations)} subjects). going deeper.')
            actual_creations = 0
            if len(creations) > 0:
                for token_address, tx_info in creations.items():
                    if is_creation_tx(token_address, tx_info):
                        token_stats = get_contract_wallet_txns(token_address, latest_block)
                        if len(token_stats) > 0:
                            print(f'\n--------------------------------')
                            with open('record_book.txt', 'r') as f:
                                if token_address in ''.join(f.readlines()):
                                    print('token already in DB')
                                elif not token_address in ''.join(f.readlines()):
                                    actual_creations += 1
                                    with open('record_book.txt', 'a') as f_w:
                                        f_w.write('Found token with potential\n')
                                        f_w.write(f'Token address: {token_address}\n')
                                        f_w.write(f'Created on block #{tx_info[0]}\n')
                                        for stat in token_stats:
                                            info_to_write = str(stat).replace("'", "") 
                                            f_w.write(f'{info_to_write}\n')

                                        print('Found token with potential')
                                        print(f'Token address: {token_address}')
                                        print(f'Created on block #{tx_info[0]}\n')
                                        for stat in token_stats:
                                            info_to_write = str(stat).replace("'", "") 
                                            print(f'{info_to_write}\n')

                                        try:
                                            print('trying to get name and symbol')
                                            abi = [{"inputs":[],
                                            "name":"name",
                                            "outputs":[{
                                                "internalType":"string",
                                                "name":"",
                                                "type":"string"}],
                                            "stateMutability":"view",
                                            "type":"function"},
                                            {"inputs":[],
                                            "name":"symbol",
                                            "outputs":[{
                                                "internalType":"string",
                                                "name":"",
                                                "type":"string"}],
                                            "stateMutability":"view",
                                            "type":"function"}]

                                            contract = w3.eth.contract(token_address , abi = abi)
                                            token_name = contract.functions.name().call()
                                            token_symbol = contract.functions.symbol().call()

                                            f_w.write(f'Name: {token_name}\n')
                                            f_w.write(f'Symbol: {token_symbol}\n')

                                            print(f'Name: {token_name}')
                                            print(f'Symbol: {token_symbol}')
                                            for stat in token_stats:
                                                await bot.sendMessage(chat_id='@th3k1ll3r', text=f"{token_symbol}: {stat['image_url']}")
                                                await bot.sendMessage(chat_id='@th3k1ll3r', text=f"current token price: {stat['relative_token_price']}\n\n(https://coinmarketcap.com/dexscan/{chain}/{stat['contract_wallet_address']})\n\n({bscscan_api.replace('api.','').replace('/api/', '')}/token/{token_address})")
                                            print('saved name and symbol')
                                        except:
                                            print('could not parse name and symbol...')
                                        f_w.write('\n')
                                        f_w.close()
                                f.close()
                            print(f'--------------------------------\n')
                    time.sleep(1)

            print(f'Found {actual_creations} potential mooners from {len(creations)} subjects.')
            knockout = (back_stretch*3)*0.1
            print(f'Finished search round in {round(time.time()-p_start)} seconds.')
            print(f'Taking a well deserved {round(knockout/60)}-minute break...')
            time.sleep(knockout)

def main():
    asyncio.run(func())

thread = threading.Thread(target=main,)
thread.start()
app = FastAPI()

@app.get("/")
async def confirm(request: Request):
    return """My process is purely logistical, narrowly focused by design. I’m not here to take sides. It’s not my place to formulate any opinion. No one who can afford me needs to waste time winning me to some cause."""
