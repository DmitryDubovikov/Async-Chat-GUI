import asyncio
from dotenv import load_dotenv
import os
import argparse
import logging
import json
import aiofiles
from contextlib import aclosing


async def register(reader, writer):
    data = await reader.read(1024)
    response = data.decode()
    logging.info(f"Recieved response: {response}")

    # Enter empty personal hash to create new account
    message = "\n"
    writer.write(message.encode())
    await writer.drain()

    data = await reader.read(1024)
    response = data.decode()
    logging.info(f"Recieved response: {response}")

    message = input("Enter preferred nickname below: ").replace("\n", "") + "\n"
    logging.info(f"Sending message: {message}")
    writer.write(message.encode() + b"\n")
    await writer.drain()

    data = await reader.readline()
    response = data.decode().strip()
    logging.info(f"Recieved response: {response}")

    data_dict = json.loads(response)
    account_hash = data_dict.get("account_hash")

    async with aiofiles.open(".env", "w") as env_file:
        await env_file.write(f"ACCOUNT_HASH={account_hash}")


async def main(host, port):
    async with aclosing(await asyncio.open_connection(host, port)) as (reader, writer):
        await register(reader, writer)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Connect to a chat server.")
    parser.add_argument(
        "--host",
        type=str,
        default="minechat.dvmn.org",
        help="Host name of the chat server",
    )
    parser.add_argument(
        "--port", type=int, default=5050, help="Port number of the chat server"
    )

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    asyncio.run(main(args.host, args.port))
