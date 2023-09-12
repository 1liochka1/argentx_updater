import asyncio
import json

from loguru import logger
from starknet_py.contract import Contract
from starknet_py.hash import selector
from starknet_py.hash.address import compute_address
from starknet_py.net.account.account import Account
from starknet_py.net.gateway_client import GatewayClient
from starknet_py.net.models import StarknetChainId
from starknet_py.net.signer.stark_curve_signer import KeyPair
from web3 import Web3
from web3.eth import AsyncEth

from config import min_eth_balance, gwei

ARGENT_CLASS_HASH = 0x33434ad846cdd5f23eb73ff09fe6fddd568284a0fb7d1be20ee482f044dabe2

ARGENT_PROXY_CLASS_HASH = 0x25ec026985a3bf9d0cc1fe17326b245dfdc3ff89b8fde106542a3ea56c5a918

NEW_ARGENT_CLASS_HASH = 0x1a736d6ed154502257f02b1ccdf4d9d1089f80811cd6acad48e6b6a9d1f2003

scan = 'https://starkscan.co/tx/'


async def create_constructor_call_data(account_class_hash, public_key):
    account_initialize_call_data = [public_key, 0]
    return [
        account_class_hash,
        selector.get_selector_from_name("initialize"),
        len(account_initialize_call_data),
        *account_initialize_call_data,
    ]


async def get_address(key):
    public = KeyPair.from_private_key(int(key[2:], 16)).public_key
    address = compute_address(
        salt=public,
        class_hash=ARGENT_PROXY_CLASS_HASH,
        constructor_calldata=await create_constructor_call_data(ARGENT_CLASS_HASH, public),
        deployer_address=0
    )
    return hex(address)


async def check_update(contract: Contract):
    version = await contract.functions['getVersion'].call()
    version = bytes.fromhex(hex(version.as_tuple()[0])[2:]).decode('utf-8')
    if version == '0.2.3':
        logger.debug('Требуется апдейт!')
        return True
    else:
        logger.debug('Апдейт не требуется')
        return False

async def check_gas():
    while True:
        try:
            w3 = Web3(Web3.AsyncHTTPProvider('https://rpc.ankr.com/eth'), modules={'eth': (AsyncEth,)}, middlewares=[])
            gas = await w3.eth.gas_price
            gas_ = w3.from_wei(gas, 'gwei')
            logger.success(f'gwei сейчас - {gas_}...')
            if gwei > gas_:
                return True
            logger.error(f'gwei слишком большой, жду понижения...')
            await asyncio.sleep(30)
        except Exception as e:
            logger.error(e)
            await asyncio.sleep(2)
            return await check_gas()

async def update_wallet(key):
    with open('abi.json', 'r') as f:
        abi = json.load(f)
    address = await get_address(key)
    try:
        account = Account(address=address,
                          client=GatewayClient(net='mainnet'),
                          key_pair=KeyPair.from_private_key(int(key[2:], 16)),
                          chain=StarknetChainId.MAINNET)
        self_contract = Contract(address, abi, account)
        if not await check_update(self_contract):
            return 'already updated'
        update_call = self_contract.functions['upgrade'].prepare(NEW_ARGENT_CLASS_HASH, [0])
        balance = await account.get_balance('0x049d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7',
                                            StarknetChainId.MAINNET) / 10 ** 18
        if balance < min_eth_balance:
            logger.error(f'{address} - баланс {balance} eth недостаточен для апдейта кошелька...')
            return False
        await check_gas()
        tx = await account.execute(calls=update_call, auto_estimate=True)
        status = await account.client.wait_for_tx(tx.transaction_hash)
        if status.status.name in ['SUCCEEDED', 'ACCEPTED_ON_L1', 'ACCEPTED_ON_L2']:
            logger.success(
                f'{address} - транзакция подтвердилась, аккаунт успешно обновлен {scan}{hex(tx.transaction_hash)}')
            return 'updated'
        else:
            logger.error(f'{address} - транзакция неуспешна...')
            return 'error in tx'
    except Exception as e:
        error = str(e)
        if 'StarknetErrorCode.INSUFFICIENT_ACCOUNT_BALANCE' in error:
            logger.error(f'{address} - Не хватает баланса на деплой аккаунта...')
            return 'not balance'
        else:
            logger.error(f'{address} - ошибка {e}')
        return e



