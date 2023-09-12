import asyncio
import csv
import random

from config import delay
from utils import update_wallet
from loguru import logger


async def add_to_csv(wallet_info, path='results.csv'):
    with open(path, 'a', newline='') as file:
        writer = csv.writer(file)
        if file.tell() == 0:
            writer.writerow(['key', 'result'])
        writer.writerow([*wallet_info])


async def main():
    with open("keys.txt", "r") as f:
        keys = [row.strip() for row in f]
    random.shuffle(keys)
    for key in keys:
        res = await update_wallet(key)
        await add_to_csv((key, res))
        t = random.randint(*delay)
        logger.info(f'сплю {t} секунд')
        await asyncio.sleep(t)


if __name__ == '__main__':
    print(f'\n{" " * 32}автор - https://t.me/iliocka{" " * 32}\n')
    asyncio.run(main())
    logger.success(f'muнетинг закончен...')
    print(f'\n{" " * 32}автор - https://t.me/iliocka{" " * 32}\n')
    print(f'\n{" " * 32}donate - EVM 0xFD6594D11b13C6b1756E328cc13aC26742dBa868{" " * 32}\n')
    print(f'\n{" " * 32}donate - trc20 TMmL915TX2CAPkh9SgF31U4Trr32NStRBp{" " * 32}\n')
