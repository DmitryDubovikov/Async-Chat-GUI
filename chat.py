import argparse
import asyncio
import logging
import os
from contextlib import aclosing
from datetime import datetime

import aiofiles
from dotenv import load_dotenv

import gui


async def send_test_messages(sending_queue):
    while True:
        await sending_queue.put(datetime.timestamp(datetime.now()))
        await asyncio.sleep(10)


async def send_messages(writer, sending_queue):
    while True:
        message = await sending_queue.get()
        logging.info(f"Sending message: {message}")
        writer.write(message.encode() + b"\n")
        await writer.drain()
        logging.info(f"Message '{message}' sent.")


async def read_messages(reader, messages_queue, history_filename):
    while True:
        data = await reader.read(1024)
        if not data:
            break

        message = data.decode().strip()
        await messages_queue.put(message)

        async with aiofiles.open(history_filename, mode="a") as file:
            await file.write(message + "\n")


async def open_connection_and_write(
    host, port, messages_queue, sending_queue, account_hash
):
    try:
        async with aclosing(await asyncio.open_connection(host, port)) as (
            reader,
            writer,
        ):
            authorised = await authorise(reader, writer, account_hash)
            if not authorised:
                print("Неизвестный токен. Проверьте его или зарегистрируйте заново.")
                return
            await send_messages(writer, sending_queue)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        if not reader.at_eof():
            reader.feed_eof()
        writer.close()
        await writer.wait_closed()


async def open_connection_and_read(host, port, messages_queue, history_filename):
    while True:
        try:
            reader, _ = await asyncio.open_connection(host, port)
            async with aclosing(reader):
                await read_messages(reader, messages_queue, history_filename)
        except Exception as e:
            logging.error(f"An error occurred: {e}")

        # Sleep for some time before trying to reconnect
        await asyncio.sleep(5)


async def restore_messages(messages_queue, history_filename):
    async with aiofiles.open(history_filename, mode="r") as file:
        lines = await file.readlines()
        for line in lines:
            message = line.strip()
            await messages_queue.put(message)


async def authorise(reader, writer, account_hash):
    message = account_hash + "\n"
    writer.write(message.encode())
    await writer.drain()

    data = await reader.read(1024)
    response = data.decode()
    if "null" in response:
        return False
    return True


async def main(host, port_read, port_write, history_filename):
    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    load_dotenv()
    account_hash = os.getenv("ACCOUNT_HASH")

    await restore_messages(messages_queue, history_filename)

    await asyncio.gather(
        open_connection_and_read(host, port_read, messages_queue, history_filename),
        open_connection_and_write(
            host, port_write, messages_queue, sending_queue, account_hash
        ),
        gui.draw(messages_queue, sending_queue, status_updates_queue),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Connect to a chat server.")
    parser.add_argument(
        "--host",
        type=str,
        default="minechat.dvmn.org",
        help="Host name of the chat server",
    )
    parser.add_argument(
        "--port_read",
        type=int,
        default=5000,
        help="Read port number of the chat server",
    )
    parser.add_argument(
        "--port_write",
        type=int,
        default=5050,
        help="Write port number of the chat server",
    )
    parser.add_argument(
        "--history",
        type=str,
        default="minechat.history",
        dest="history_filename",
        help="History filename to read messages from",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    asyncio.run(main(args.host, args.port_read, args.port_write, args.history_filename))
