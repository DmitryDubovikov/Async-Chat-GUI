import argparse
import asyncio
import json
import logging
import os
import sys
from contextlib import aclosing
from tkinter import messagebox

import aiofiles
from dotenv import load_dotenv

import gui


class InvalidToken(Exception):
    pass


async def send_messages(writer, sending_queue):
    while True:
        message = await sending_queue.get()
        message = message.replace("\n", "") + "\n"
        # logging.info(f"Sending message: {message}")
        writer.write(message.encode() + b"\n")
        await writer.drain()
        # logging.info(f"Message '{message}' sent.")


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
            try:
                user = await authorise(reader, writer, account_hash)
                logging.info(f"Выполнена авторизация. Пользователь {user}.")
                await send_messages(writer, sending_queue)
            except InvalidToken as e:
                logging.error(f"An error occurred: {e}")
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        sys.exit()
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


def get_nickname(input_string):
    start_index = input_string.find("{")
    end_index = input_string.find("}") + 1

    json_data = input_string[start_index:end_index]

    # Распарсить JSON-данные и получить значение по ключу "nickname"
    try:
        data = json.loads(json_data)
        nickname = data["nickname"]
        return nickname
    except json.JSONDecodeError as e:
        return f"Error decoding JSON: {e}"
    except KeyError as e:
        return f"KeyError: 'nickname' key not found in JSON data"


async def authorise(reader, writer, account_hash):
    message = account_hash + "\n"
    writer.write(message.encode())
    await writer.drain()

    data = await reader.read(1024)
    response = data.decode()
    if "null" in response:
        messagebox.showerror(
            "Ошибка",
            "Неверный токен. Пожалуйста, проверьте ваш токен и попробуйте снова.",
        )
        raise InvalidToken("Неверный токен получен от сервера.")
    return get_nickname(response)


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
