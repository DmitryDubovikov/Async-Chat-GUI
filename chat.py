import argparse
import asyncio
import logging
import os
from contextlib import aclosing
from datetime import datetime

import aiofiles
from dotenv import load_dotenv

import gui


async def send_test_messages(messages_queue):
    while True:
        await messages_queue.put(datetime.timestamp(datetime.now()))
        await asyncio.sleep(10)


async def send_message(host, port, messages_queue):
    while True:
        msg = await messages_queue.get()
        print(msg)


async def read_messages(reader, messages_queue, history_filename):
    while True:
        data = await reader.read(1024)
        if not data:
            break

        message = data.decode().strip()
        await messages_queue.put(message)

        async with aiofiles.open(history_filename, mode="a") as file:
            await file.write(message + "\n")


async def open_connection_and_read(
    host, port, messages_queue, history_filename, account_hash
):
    while True:
        try:
            async with aclosing(await asyncio.open_connection(host, port)) as (
                reader,
                writer,
            ):
                authorised = await authorise(reader, writer, account_hash)
                if not authorised:
                    print(
                        "Неизвестный токен. Проверьте его или зарегистрируйте заново."
                    )
                    return
                logging.info(f"Выполнена авторизация. Пользователь {authorised}.")
                await read_messages(reader, messages_queue, history_filename)
        except Exception as e:
            logging.error(f"An error occurred: {e}")
        finally:
            if not reader.at_eof():
                reader.feed_eof()
            writer.close()
            await writer.wait_closed()

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


async def main(host, port, history_filename):
    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_updates_queue = asyncio.Queue()

    load_dotenv()
    account_hash = os.getenv("ACCOUNT_HASH")

    await restore_messages(messages_queue, history_filename)

    await asyncio.gather(
        open_connection_and_read(
            host, port, messages_queue, history_filename, account_hash
        ),
        send_message(host, port, sending_queue),
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
        "--port", type=int, default=5000, help="Port number of the chat server"
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

    asyncio.run(main(args.host, args.port, args.history_filename))
