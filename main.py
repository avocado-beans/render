from fastapi import FastAPI, Request
from web3 import Web3
import threading
import traceback
import requests
import telegram
import asyncio
import time
import os

wbnb_address = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2'
bscusd_address = '0xdac17f958d2ee523a2206206994597c13d831ec7'
provider_url = 'https://eth-pokt.nodies.app'
bscscan_api = 'https://api.etherscan.io/api/'
bscscan_api_key = str(os.environ['ETHCHAINAPI'])
bnbprice = 'ethprice'
chain = 'ethereum'
chat_id = '-1002184767994'

blockspermin = 20
minutes = 5
back_stretch_minutes = 60
width = minutes*blockspermin
back_stretch = back_stretch_minutes*blockspermin
front_limit = back_stretch - width

def latest_bnb_price():
    url = bscscan_api
    params = {
	'module': 'stats',
	'action': bnbprice,
	'apikey': bscscan_api_key,
    }
    response = requests.get(url, params=params)
    return float(response.json()['result']['ethusd'])

def get_creation_tx_hash(token_address):
    url = bscscan_api
    params = {
	'module': 'contract',
	'action': 'getcontractcreation',
	'contractaddresses': Web3.to_checksum_address(token_address),
	'apikey': bscscan_api_key,
    }
    response = requests.get(url, params=params)
    try:
        return response.json()['result'][0]['txHash']
    except:
        print(f'encountered creation tx exception: {token_address}')
        print(traceback.format_exc())
        print(response.json())
        time.sleep(300)
        return '0x0'

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

async def func():
    global w3
    global TRANSFER_EVENT_SIGNATURE
    w3 = Web3(Web3.HTTPProvider(provider_url))
    print(w3.is_connected())
    TRANSFER_EVENT_SIGNATURE = w3.keccak(text='Transfer(address,address,uint256)').hex()

    bot = telegram.Bot(os.environ['TELEBOTAPI'])
    await bot.sendMessage(chat_id=chat_id, text=f"code base modified\nrebooted to apply updates")
    time.sleep(10)
    await bot.sendMessage(chat_id=chat_id, text=f"target chain: {chain.lower()}")
    time.sleep(2)
    await bot.sendMessage(chat_id=chat_id, text="bravo6\ngoing dark")
    print("bravo6\ngoing dark")

    while True:
        p_start = time.time()
        latest_block = w3.eth.block_number

        print('\n***************************************')
        print(f'checking what happened (~{back_stretch/(60*blockspermin)}hrs) ago on {chain.upper()}...')
        no_of_chunks = round(minutes/5)

        print(f'took {latest_block} as latest block')
        hit_wall = False
        for i in range(no_of_chunks):
            if back_stretch - width*(i+1) < front_limit:
                print('hit a wall')
                hit_wall = True
                break
            print(f'parsing chunk {i+1}: { latest_block - (back_stretch - width*i)} to { latest_block - (back_stretch - width*(i+1))}')
            filter_params = {
                    'fromBlock': latest_block - (back_stretch - width*i),
                    'toBlock': latest_block - (back_stretch - width*(i+1)),
                    'topics': [TRANSFER_EVENT_SIGNATURE]
                }
            logs = w3.eth.get_logs(filter_params)
            print('finished parsing chunk')
            if i == 0:
                t_logs = logs
            elif i > 0:
                t_logs += logs
        if hit_wall:
            time.sleep(60)
            continue
        creations = {}
        print(f'Done parsing logs ({len(logs)}). now analyzing...')

        previous_session = open('record_book.txt', 'r')
        previous_session_info = ''.join(previous_session.readlines())
        previous_session.close()
        tokens = []
        for log in t_logs:
            try:
                value = int.from_bytes(log['data'], byteorder='big')
                zeroes = str(value).replace('.','').count('0')
                sender_address = str(w3.to_hex(log['topics'][1]))
                recipient_address = str(w3.to_hex(log['topics'][2]))

                if is_null(sender_address, 'x') is True \
                    and is_null(recipient_address, 'x') is False \
                    and (value / 10**9) >= 10**6 \
                    and (not log['address'] in tokens) \
                    and (not log['address'] in previous_session_info):
                    if recipient_address[:26] == '0x000000000000000000000000' and len(recipient_address) > 60:
                        recipient_address = f'0x{recipient_address[26:]}'

                    creations.update({f"{log['address']}": [int(log['blockNumber']), log['transactionHash'].hex()]})
                    tokens.append(log['address'])
            except:
                pass

        print(f'created ledger ({len(creations)} subjects). going deeper.')
        actual_creations = 0
        if len(creations) > 0:
            for token_address, tx_info in creations.items():
                if is_creation_tx(token_address, tx_info):
                    token_stats = get_contract_wallet_txns(token_address, latest_block, back_stretch)
                    if len(token_stats) > 0:
                        print(f'\n--------------------------------\n')
                        actual_creations += 1
                        with open('record_book.txt', 'a') as f_w:
                            f_w.write(f'{token_address}, \n')
                            f_w.close()
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

                            print(f'Name: {token_name}')
                            print(f'Symbol: {token_symbol}')
                            for stat in token_stats:
                                text = msg_construct(token_address, stat)
                                message = (await bot.sendMessage(chat_id=chat_id, text=f"🟢{token_symbol}🟢\n\n{text}", parse_mode = 'MarkdownV2')) if (bool(stat['is_locked'])) else (await bot.sendMessage(chat_id=chat_id, text=f"⚠{token_symbol}⚠\n\n{text}", parse_mode = 'MarkdownV2'))
                        except:
                            print(traceback.format_exc())
                            print('could not parse name and symbol...')
                        print(f'\n--------------------------------\n')
        print(f'Found {actual_creations} potential mooners from {len(creations)} subjects.')
        absence = time.time()-p_start
        print(f'Finished search round in {round(absence)} seconds.')
        knockout = 300
        if knockout - absence > 0:
            print(f'Taking a well deserved {round((knockout - absence)/60)}-minute break...')
            time.sleep(knockout - absence)

def msg_construct(token_address, stat):
    token_addressHL = f"{bscscan_api.replace('api.','').replace('/api/', '')}/token/{token_address}"
    lp_addressHL = f"{bscscan_api.replace('api.','').replace('/api/', '')}/token/{stat['contract_wallet_address']}"
    cmcHL = f"https://coinmarketcap.com/dexscan/{chain}/{stat['contract_wallet_address']}"
    price = stat['relative_token_price']
    price = str(round(float(price[:price.index('e')]), 4)) + price[price.index('e'):]
    price = '$'+price.replace('.', '\\.').replace('e', ' x 10^').replace('-0', '-').replace('-', '\\-')
	
    text = f"Current Price: [{price}]({cmcHL})\nToken Address: [{token_address}]({token_addressHL})\nLP Address: [{stat['contract_wallet_address']}]({lp_addressHL})\n"
    return text
	
def lockedburned(lp_address, from_block):
    filter_params = {
	'fromBlock': from_block,
	'toBlock': w3.eth.block_number,
	'address': Web3.to_checksum_address(lp_address),
	'topics': [TRANSFER_EVENT_SIGNATURE]}
    logs = w3.eth.get_logs(filter_params)

    burner = '0x000000000000000000000000000000000000dead'
    uncx = '0x663a5c229c09b049e36dcc11a9b0d4a8eb9db214'
    teamfinance = '0xe2fe530c047f2d85298b07d9333c05737f1435fb'
    pinklock = '0x71b5759d73262fbb223956913ecf4ecc51057641'
    lockersburners = [uncx, teamfinance, pinklock]

    logs = logs[:100]
    for log in logs:
        sender_address = str(w3.to_hex(log['topics'][1]))
        recipient_address = str(w3.to_hex(log['topics'][2]))

        for address in [sender_address, recipient_address]:
            address = f'0x{address[26:]}'
            if address in lockersburners:
                return True
    return False

def send_req(url, params):
    RETRY = 0
    while (RETRY < 3):
        try:
            start = time.time()
            response = requests.get(url, params=params)
            spare_time = 0.5 - (time.time()-start)
            if spare_time > 0:
                time.sleep(spare_time)
            return response
        except:
            RETRY += 1
            time.sleep(2)
    return -1

def is_lpage(lp_address):
    url = f'https://coinmarketcap.com/dexscan/{chain}/{lp_address}/'
    try:
        response = requests.get(url)
        img = response.text.split('class="dex-pairs-name"><img class="token-icon" src="')[1].split('" width="')[0]
        return True
    except:
        return False

def is_creation_tx(token_address, tx_info):
    start = time.time()
    is_creation = True if (get_creation_tx_hash(token_address) == tx_info[1]) else False
    return is_creation
	
def address_type(wallet_address):
    code = str(w3.to_hex(w3.eth.get_code(Web3.to_checksum_address(wallet_address))))
    address_type = {'address_type': 'contract_address'} if (len(code) > 3) else {'address_type': 'externally_owned_address'}
    return address_type
	
def is_null(address, anchor):
    if (len(address.replace(anchor, '')) == address.replace(anchor, '').count('0')):
        return True
    return False

def get_contract_wallet_txns(token_address, latest_block, back_stretch):
    filter_params = {
	'fromBlock': latest_block - back_stretch,
	'toBlock': w3.eth.block_number,
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
        blockNum = int(log['blockNumber'])
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
                        if is_lpage(address):
                            is_locked = lockedburned(address, blockNum)
                            print('audited one possible LP')
                            if (wbnb_balance > 1):
                                relative_token_price = (wbnb_balance*latest_bnb_price())/token_balance
                            if (usd_balance > 1):
                                relative_token_price = usd_balance/token_balance

                            response ={
                                f'contract_wallet_address': address,
                                f'relative_token_price': str("{:e}".format(relative_token_price)),
                                f'token_balance': token_balance,
                                f'wbnb_balance': wbnb_balance,
                                f'bsc-usd_balance': usd_balance,
                                f'is_locked': is_locked
                                }

                            balance_book.append(response)

    if len(balance_book) > 0:
        print(f'Found {len(balance_book)} potential LPs for the token: {token_address}')
    print(f'finished in {round(time.time()-start)} seconds')
    return(balance_book)
	
def main():
    if True:
        try:
            asyncio.run(func())
        except:
            print(traceback.format_exc())
            time.sleep(60)
		
mainthread = threading.Thread(target=main,)
mainthread.start()

app = FastAPI()
@app.get("/")
async def confirm(request: Request):
    return """My process is purely logistical, narrowly focused by design. I’m not here to take sides. It’s not my place to formulate any opinion. No one who can afford me needs to waste time winning me to some cause."""
