from fastapi import FastAPI, Request
from web3 import Web3
import os, traceback
import threading
import telegram
import requests
import asyncio
import time

chain = 'bsc'
chain_id = {
'ethereum': 1,
'bsc': 56,
}
chat_id = '-1002184767994'
scannerkey = os.environ['BSCCHAINAPI']
scannerurl = 'https://api.bscscan.com/api/'
counter_tkns = ['0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c', '0x55d398326f99059ff775485246999027b3197955', '0xe9e7cea3dedca5984780bafc599bd69add087d56']

explorerurl = 'https://bscscan.com'
ethprice = 'bnbprice'
provider_url = 'https://bsc-pokt.nodies.app' #f"https://bsc-mainnet.infura.io/v3/{os.environ['INFURAKEY']}"
abi = [{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"}]

blockspermin = 20
minutes = 5
back_stretch_minutes = 30
width = minutes*blockspermin
back_stretch = back_stretch_minutes*blockspermin

tokens = []
def get_source(token_address):
    url = scannerurl
    params = {
	'module': 'contract',
	'action': 'getsourcecode',
	'address': Web3.to_checksum_address(token_address),
	'apikey': scannerkey,
    }
    return True if ('require(currentAllowance == 0' in str(requests.get(url, params=params).json()['result'][0]['SourceCode'])) else False

def get_creator_address(token_address):
    url = scannerurl
    params = {
	'module': 'contract',
	'action': 'getcontractcreation',
	'contractaddresses': Web3.to_checksum_address(token_address),
	'apikey': scannerkey,
    }
    return requests.get(url, params=params).json()['result'][0]['contractCreator']

def latest_eth_price():
    url = scannerurl
    params = {
	'module': 'stats',
	'action': ethprice,
	'apikey': scannerkey,
    }
    response = requests.get(url, params=params)
    return float(response.json()['result']['ethusd'])

def msg_construct(token_address, pair_address, price):
    token_addressHL = f"{explorerurl}/token/{token_address}"
    lp_addressHL = f"{explorerurl}/token/{pair_address}"
    cmcHL = f"https://coinmarketcap.com/dexscan/{chain}/{pair_address}"
    price = str(round(float(price[:price.index('e')]), 4)) + price[price.index('e'):]
    price = '$'+price.replace('e', ' x 10^').replace('-0', '-')

    text = f"Current Price: {price}\n({cmcHL})\nToken Address: {token_address}\n({token_addressHL})\nLP Address: {pair_address}\n({lp_addressHL})\n"
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

    uncx = '0xC765bddB93b0D1c1A88282BA0fa6B2d00E3e0c83'.lower()
    teamfinance = '0xe2fe530c047f2d85298b07d9333c05737f1435fb'
    pinklock = '0x407993575c91ce7643a4d4ccacc9a98c36ee1bbe'

    lockers = [uncx, pinklock, burner]

    logs = logs[:100]
    for log in logs:
        sender_address = str(w3.to_hex(log['topics'][1]))
        recipient_address = str(w3.to_hex(log['topics'][2]))

        for address in [sender_address, recipient_address]:
            address = f'0x{address[26:]}'
            if address.lower() in lockers:
                return True
    return False

def get_abi(token_address):
    url = scannerurl
    params = {
	'module': 'contract',
	'action': 'getabi',
	'address': Web3.to_checksum_address(token_address),
	'apikey': scannerkey,
    }
    return requests.get(url, params=params).json()['result']

def get_balance(wallet_address, token_address):
    url = scannerurl
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
        l_abi = get_abi(token_address)
        token = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=l_abi) # declaring the token contract
        try:
            decimals = int(token.functions.decimals().call())
        except:
            decimals = 18

        return float(balance)/(10**decimals)
    except:
        return -1

def check_ownership(token_address):
    try:
        contract = w3.eth.contract(address=Web3.to_checksum_address(token_address), abi=get_abi(token_address))
        token_owner = contract.functions.owner().call()
        return token_owner
    except:
        print('Owner is Hidden')
    return None

def latest_token_price(token_address, counter_address, pair_address):
    token_balance = get_balance(pair_address, token_address)
    if token_balance > 0 and (counter_address.lower() in counter_tkns):
        counter_balance = get_balance(pair_address, counter_address)
        price = (counter_balance*latest_eth_price())/token_balance if (counter_address.lower() == counter_tkns[0]) else counter_balance/token_balance
        return price
    return 0

def security_audit(token_address):
    url = f'https://api.gopluslabs.io/api/v1/token_security/{chain_id[chain.lower()]}'
    params = {'contract_addresses': token_address}
    response = requests.get(url, params=params).json()['result']
    response = response[token_address.lower()] if len(response) > 0 else None

    contract_checks = [{'is_open_source': '0'},{'is_proxy': '1'},{'is_mintable': '1'},{'can_take_back_ownership': '1'},{'owner_change_balance': '1'},{'hidden_owner': '1'},{'selfdestruct': '1'},{'external_call': '1'}]
    honeypot_checks = [{'is_honeypot': '1'},{'transfer_pausable': '1'},{'cannot_sell_all': '1'},{'cannot_buy': '1'},{'trading_cooldown': '1'},{'is_anti_whale': '1'},{'anti_whale_modifiable': '1'},{'slippage_modifiable': '1'},{'is_blacklisted': '1'},{'is_whitelisted': '1'},{'personal_slippage_modifiable': '1'}]

    high_risks = [
        {'is_open_source': '0'},
        {'is_proxy': '1'},
        {'is_mintable': '1'},
        {'can_take_back_ownership': '1'},
        {'owner_change_balance': '1'},
        {'hidden_owner': '1'},
        {'selfdestruct': '1'},
        {'external_call': '1'},
        {'is_honeypot': '1'},
        {'cannot_sell_all': '1'},
        {'cannot_buy': '1'},
    ]

    if response:
        sell_tax = float(response['sell_tax']) if (('sell_tax' in response) and (response['sell_tax'].replace(' ', '') != '')) else 1.0
        buy_tax = float(response['buy_tax']) if (('buy_tax' in response) and (response['buy_tax'].replace(' ', '') != '')) else 1.0
        owner = response['owner_address'] if (('owner_address' in response) and (response['owner_address'].replace(' ', '') != '')) else None

        contract_alerts = {}
        honeypot_alerts = {}
        high_alerts = {}
        for item, status in response.items():
            contract_alerts.update({item: status}) if {item: status} in contract_checks else None
            honeypot_alerts.update({item: status}) if {item: status} in honeypot_checks else None
            high_alerts.update({item: status}) if {item: status} in high_risks else None

        tax = {'sell': sell_tax, 'buy': buy_tax,}
        return {'contract_security':{}, 'honeypot_risks':{}, 'high_risks':high_alerts, 'tax': tax, 'owner': owner}
    else:
        return {'contract_security':contract_checks,
                'honeypot_risks':honeypot_checks,
                'high_risks':high_risks,
                'tax': {'sell':1.0,'buy':1.0},
                'owner': None}

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
        from_block = latest_block - (back_stretch)
        to_block = latest_block - (back_stretch - width)
        print(f'Parsing logs from {from_block} to {to_block}')

        temp_tokens = []
        filter_params = {
    	'fromBlock': from_block,
    	'toBlock': to_block,
    	'topics': [CREATION_EVENT_SIGNATURE]}
        logs = w3.eth.get_logs(filter_params)
        print(len(logs))

        for log in logs:
            time.sleep(1)
            token_address =  Web3.to_checksum_address(f"0x{str(w3.to_hex(log['topics'][1]))[26:]}") if (not f"0x{str(w3.to_hex(log['topics'][1]))[26:]}" in counter_tkns) else Web3.to_checksum_address(f"0x{str(w3.to_hex(log['topics'][2]))[26:]}")
            counter_address = Web3.to_checksum_address(f"0x{str(w3.to_hex(log['topics'][2]))[26:]}") if (f"0x{str(w3.to_hex(log['topics'][2]))[26:]}" in counter_tkns) else Web3.to_checksum_address(f"0x{str(w3.to_hex(log['topics'][1]))[26:]}")
            pair_address = Web3.to_checksum_address(f"0x{str(w3.to_hex(log['data']))[26:66]}")
            contract = w3.eth.contract(token_address , abi=abi)
            token_name = contract.functions.name().call()
            token_symbol = contract.functions.symbol().call()
            temp_tokens.append(token_address)

            if token_address in tokens:
                continue
            try:
                security_scan = security_audit(token_address)
            except:
                continue
            if (security_scan['tax']['sell']>0.1) or (security_scan['tax']['buy']>0.1) or (len(security_scan['high_risks'])>0) or (len(security_scan['contract_security'])>0):
                print(security_scan['high_risks'])
                print(token_address)
                pass
            owner = security_scan['owner'] if (security_scan['owner'] != None) else check_ownership(token_address)
            if owner is None:
                print(token_address)
                pass

            counter_balance = get_balance(pair_address, counter_address)*latest_eth_price() if (counter_address == counter_tkns[0]) else get_balance(pair_address, counter_address)
            price = latest_token_price(token_address, counter_address, pair_address)
            if (price > 0): # and (counter_balance > 1):
                print(f'Name: {token_name}')
                print(f'Symbol: {token_symbol}')
                print(pair_address)
                print(security_scan['tax'])
                print(len(security_scan['high_risks']), len(security_scan['contract_security']))
                price = str("{:e}".format(price))
                is_locked = locked(pair_address, int(log['blockNumber']))
                message = msg_construct(token_address, pair_address, price)
                text = f"Staked Token: {counter_address}\nSell and Buy Tax: {security_scan['tax']['sell']}, {security_scan['tax']['buy']}\nLiquidity Locked, Staked BNB Value: ${round(counter_balance)}\n- Creator Address: {get_creator_address(token_address)}\n- Owner Address: {owner}\n\nSymbol: {token_symbol}\n{message}" if (is_locked) else f"Staked Token: {counter_address}\nSell and Buy Tax: {security_scan['tax']['sell']}, {security_scan['tax']['buy']}\nLiquidity NOT Locked, Staked BNB Value: ${round(counter_balance)}\n- Creator Address: {get_creator_address(token_address)}\n- Owner Address: {owner}\n\nSymbol: {token_symbol}\n{message}"
                print(text)
                send_message = (await bot.sendMessage(chat_id=chat_id, text=text))# if (is_locked) else temp_tokens.remove(token_address)

        for token in tokens:
            if not token in temp_tokens:
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
