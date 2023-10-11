## Chat Client

This is a simple chat client script that connects to a chat server and reads messages from it. It supports the ability to specify the host name, port number, and history filename as command-line arguments.

### Prerequisites

- Python 3.7 or higher
- Virtualenv (for managing the Python environment)

### Installation

1. Clone this repository.
2. Create and activate a virtual environment using venv:

```bash
python3 -m venv venv
source venv/bin/activate   # For Windows: venv\Scripts\activate
```

3. Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Usage

#### Register (optional)

To run the chat registration script, use the following command with optional arguments:

```bash
python register-minechat.py --host HOST --port PORT
```
The available arguments are:

- `--host`: The host name of the chat server. Default is "minechat.dvmn.org".
- `--port`: The port number of the chat server. Default is 5050.

Enter your preferred nickname when asked. Script will create .env file with 
```
ACCOUNT_HASH=<your_account_hash>
```

#### Chatting

To run the chat use the following command with optional arguments:

```bash
python chat.py --host HOST --port_read PORT_READ --port_write PORT_WRITE --history HISTORY_FILENAME
```

The available arguments are:

- `--host`: The host name of the chat server. Default is "minechat.dvmn.org".
- `--port_read`: The read port number of the chat server. Default is 5000.
- `--port_write`: The write port number of the chat server. Default is 5050.
- `--history`: The filename to read chat messages from. Default is "minechat.history".