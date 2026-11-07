import socket
import webbrowser

import uvicorn

from audiol.studio.app import create_app
from audiol.studio.settings import Settings


def find_free_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def run_studio(settings: Settings, open_browser: bool = True) -> None:
    port = settings.port or find_free_port(settings.host)
    url = f"http://{settings.host}:{port}"
    print(f"Vibebook Studio: {url}")
    if open_browser:
        webbrowser.open(url)
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=port,
        log_level="info",
    )
