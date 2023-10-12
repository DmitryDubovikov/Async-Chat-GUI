import asyncio
import json
from contextlib import asynccontextmanager


@asynccontextmanager
async def connection(host, port):
    try:
        reader, writer = await asyncio.open_connection(host, port)
        yield reader, writer
    finally:
        writer.close()
        await writer.wait_closed()


def get_nickname(input_string):
    start_index = input_string.find("{")
    end_index = input_string.find("}") + 1

    json_data = input_string[start_index:end_index]
    data = json.loads(json_data)

    # Распарсить JSON-данные и получить значение по ключу "nickname"
    try:
        nickname = data["nickname"]
        return nickname
    except json.JSONDecodeError as e:
        return f"Error decoding JSON: {e}"
    except KeyError as e:
        return f"KeyError: 'nickname' key not found in JSON data"
