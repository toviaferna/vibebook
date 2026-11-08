import base64
import io
import json
import math
import struct
import threading
import time
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from ebooklib import epub
from PIL import Image


@pytest.fixture
def tiny_epub(tmp_path: Path) -> Path:
    book = epub.EpubBook()
    book.set_identifier("audiol-test-123")
    book.set_title("Libro de prueba")
    book.set_language("es")
    book.add_author("Autora")

    chapters = []
    for index, (title, body) in enumerate(
        [
            ("Capítulo 1", "Pues sepa V.M. que a mí llaman Lázaro."),
            ("Capítulo 2", "Mi viuda madre determinó arrimarse a los buenos."),
        ],
        start=1,
    ):
        item = epub.EpubHtml(
            title=title,
            file_name=f"chap_{index}.xhtml",
            lang="es",
        )
        item.content = f"<h1>{title}</h1><p>{body}</p>"
        book.add_item(item)
        chapters.append(item)

    book.toc = tuple(chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", *[chapter.id for chapter in chapters]]

    path = tmp_path / "tiny.epub"
    epub.write_epub(str(path), book)
    return path


@pytest.fixture
def block_text_epub(tmp_path: Path) -> Path:
    book = epub.EpubBook()
    book.set_identifier("audiol-test-block-123")
    book.set_title("Libro con bloques")
    book.set_language("es")
    book.add_author("Autora")

    chapters = []
    for index, (title, body) in enumerate(
        [
            (
                "Capítulo de bloque",
                "<h1>Capítulo de bloque</h1><div>Texto del capítulo sin párrafos.</div>",
            ),
            (
                "Capítulo suelto",
                "<h1>Capítulo suelto</h1>Texto suelto sin etiquetas.",
            ),
        ],
        start=1,
    ):
        item = epub.EpubHtml(
            title=title,
            file_name=f"block_{index}.xhtml",
            lang="es",
        )
        item.content = body
        book.add_item(item)
        chapters.append(item)

    book.toc = tuple(chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", *[chapter.id for chapter in chapters]]

    path = tmp_path / "blocks.epub"
    epub.write_epub(str(path), book)
    return path


@pytest.fixture
def toc_epub(tmp_path: Path) -> Path:
    book = epub.EpubBook()
    book.set_identifier("audiol-test-toc-123")
    book.set_title("Libro con índice")
    book.set_language("es")
    book.add_author("Autora")

    content = epub.EpubHtml(title="Contenido", file_name="content.xhtml", lang="es")
    content.content = (
        "<p>Front matter.</p>"
        '<p><a id="top"></a>Libro con índice</p>'
        '<p><a id="ch1"></a>1</p>'
        "<p>Primer párrafo.</p>"
        "<p>Segundo párrafo.</p>"
        '<p><a id="ch2"></a>2</p>'
        "<p>Tercer párrafo.</p>"
    )
    book.add_item(content)

    outline = epub.EpubHtml(title="Document Outline", file_name="outline.xhtml", lang="es")
    outline.content = "<h1>Document Outline</h1><ul><li>1</li><li>2</li></ul>"
    book.add_item(outline)

    continuation = epub.EpubHtml(title="Continuación", file_name="continuation.xhtml", lang="es")
    continuation.content = (
        '<p>Continuación del capítulo 2.</p><p><a id="ch3"></a>3</p><p>Cuarto párrafo.</p>'
    )
    book.add_item(continuation)

    book.toc = (
        epub.Link("content.xhtml#top", "Libro con índice", "top"),
        epub.Link("content.xhtml#ch1", "1", "ch1"),
        epub.Link("content.xhtml#ch2", "2", "ch2"),
        epub.Link("continuation.xhtml#ch3", "3", "ch3"),
        epub.Link("content.xhtml#top", "FIN", "fin"),
    )
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", content.id, continuation.id, outline.id]

    path = tmp_path / "toc.epub"
    epub.write_epub(str(path), book)
    return path


@pytest.fixture
def cover_epub(tmp_path: Path) -> Path:
    book = epub.EpubBook()
    book.set_identifier("audiol-test-cover-123")
    book.set_title("Libro con portada")
    book.set_language("es")
    book.add_author("Autora")
    book.set_cover("cover.jpg", b"\xff\xd8\xff\xe0" + b"0" * 64)

    chapter = epub.EpubHtml(title="Capítulo 1", file_name="cover_chapter.xhtml", lang="es")
    chapter.content = "<h1>Capítulo 1</h1><p>Texto con portada.</p>"
    book.add_item(chapter)
    book.toc = (chapter,)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", chapter.id]

    path = tmp_path / "cover.epub"
    epub.write_epub(str(path), book)
    return path


@pytest.fixture
def mixed_block_epub(tmp_path: Path) -> Path:
    book = epub.EpubBook()
    book.set_identifier("audiol-test-mixed-123")
    book.set_title("Libro con bloques mixtos")
    book.set_language("es")
    book.add_author("Autora")

    chapters = []
    for index, (title, body) in enumerate(
        [
            (
                "Capítulo mixto",
                "<h1>Capítulo mixto</h1>"
                "<p>Intro.</p>"
                "<blockquote>Cita.</blockquote>"
                "<div>Bloque.</div>"
                "<ul><li><p>Anidado.</p></li></ul>",
            ),
            (
                "Capítulo suelto",
                "<h1>Capítulo suelto</h1>Texto suelto.",
            ),
        ],
        start=1,
    ):
        item = epub.EpubHtml(
            title=title,
            file_name=f"mixed_{index}.xhtml",
            lang="es",
        )
        item.content = body
        book.add_item(item)
        chapters.append(item)

    book.toc = tuple(chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", *[chapter.id for chapter in chapters]]

    path = tmp_path / "mixed.epub"
    epub.write_epub(str(path), book)
    return path


@pytest.fixture
def titled_toc_epub(tmp_path: Path) -> Path:
    book = epub.EpubBook()
    book.set_identifier("audiol-test-titled-123")
    book.set_title("Libro con títulos")
    book.set_language("es")
    book.add_author("Autora")

    links = []
    chapters = []
    for index, (title, body) in enumerate(
        [
            ("La casa de los relojes", "Primer párrafo."),
            ("La voz del papel", "Segundo párrafo."),
        ],
        start=1,
    ):
        item = epub.EpubHtml(title=title, file_name=f"titled_{index}.xhtml", lang="es")
        item.content = f"<h1>{title}</h1><p>{body}</p>"
        book.add_item(item)
        chapters.append(item)
        links.append(epub.Link(item.file_name, title, f"titled-{index}"))

    book.toc = tuple(links)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", *[chapter.id for chapter in chapters]]

    path = tmp_path / "titled.epub"
    epub.write_epub(str(path), book)
    return path


@pytest.fixture
def nested_toc_epub(tmp_path: Path) -> Path:
    book = epub.EpubBook()
    book.set_identifier("audiol-test-nested-123")
    book.set_title("Libro con partes")
    book.set_language("es")
    book.add_author("Autora")

    content = epub.EpubHtml(title="Parte I", file_name="nested.xhtml", lang="es")
    content.content = (
        '<p><a id="ch1"></a>La casa</p><p>Primer párrafo.</p>'
        '<p><a id="ch2"></a>El zorro</p><p>Segundo párrafo.</p>'
    )
    book.add_item(content)
    book.toc = (
        (
            epub.Section("Parte I"),
            (
                epub.Link("nested.xhtml#ch1", "La casa", "ch1"),
                epub.Link("nested.xhtml#ch2", "El zorro", "ch2"),
            ),
        ),
    )
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", content.id]

    path = tmp_path / "nested.epub"
    epub.write_epub(str(path), book)
    return path


@pytest.fixture
def heading_chapters_epub(tmp_path: Path) -> Path:
    book = epub.EpubBook()
    book.set_identifier("audiol-test-headings-123")
    book.set_title("Libro sin índice")
    book.set_language("es")
    book.add_author("Autora")

    content = epub.EpubHtml(title="Contenido", file_name="headings.xhtml", lang="es")
    content.content = (
        "<h1>Libro sin índice</h1>"
        "<h2>La casa</h2><p>Primer párrafo.</p>"
        "<h2>El zorro</h2><p>Segundo párrafo.</p>"
    )
    book.add_item(content)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", content.id]

    path = tmp_path / "headings.epub"
    epub.write_epub(str(path), book)
    return path


@pytest.fixture
def frontmatter_epub(tmp_path: Path) -> Path:
    book = epub.EpubBook()
    book.set_identifier("audiol-test-frontmatter-123")
    book.set_title("Libro con prólogo")
    book.set_language("es")
    book.add_author("Autora")

    content = epub.EpubHtml(title="Prólogo", file_name="front.xhtml", lang="es")
    content.content = (
        '<p><a id="prologo"></a>Prólogo</p><p>Texto del prólogo.</p>'
        '<p><a id="cap1"></a>La casa</p><p>Texto del capítulo.</p>'
    )
    book.add_item(content)
    book.toc = (
        epub.Link("front.xhtml#prologo", "Prólogo", "prologo"),
        epub.Link("front.xhtml#cap1", "La casa", "cap1"),
    )
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", content.id]

    path = tmp_path / "frontmatter.epub"
    epub.write_epub(str(path), book)
    return path


@pytest.fixture
def image_epub(tmp_path: Path) -> Path:
    book = epub.EpubBook()
    book.set_identifier("audiol-test-image-123")
    book.set_title("Libro ilustrado")
    book.set_language("es")
    book.add_author("Autora")

    buffer = io.BytesIO()
    Image.new("RGB", (320, 200), (40, 90, 70)).save(buffer, "PNG")
    picture = epub.EpubImage(
        uid="fig1",
        file_name="images/fig.png",
        media_type="image/png",
        content=buffer.getvalue(),
    )
    book.add_item(picture)

    chapter = epub.EpubHtml(title="La casa", file_name="illustrated.xhtml", lang="es")
    chapter.content = (
        "<h1>La casa</h1>"
        "<p>Antes de la figura.</p>"
        '<figure><img src="images/fig.png" alt="Una casa verde" />'
        "<figcaption>La casa del bosque</figcaption></figure>"
        "<p>Después de la figura.</p>"
    )
    book.add_item(chapter)
    book.toc = (epub.Link("illustrated.xhtml", "La casa", "casa"),)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav", chapter.id]

    path = tmp_path / "illustrated.epub"
    epub.write_epub(str(path), book)
    return path


class FakePluginServer:
    def __init__(
        self,
        *,
        require_token: str | None = None,
        fail_synthesis: bool = False,
        delay: float = 0.0,
        invalid_audio: bool = False,
        plugin_id: str = "fake-plugin",
    ) -> None:
        self.require_token = require_token
        self.fail_synthesis = fail_synthesis
        self.delay = delay
        self.invalid_audio = invalid_audio
        self.info = {
            "protocol": "vep/1",
            "id": plugin_id,
            "name": "Fake VEP",
            "version": "1.0.0",
            "license": "MIT",
            "source": "https://example.com/fake-vep",
            "capabilities": {
                "languages": ["es"],
                "styles": [],
                "timings": "segment",
                "streaming": False,
            },
            "limits": {
                "max_chars": 400,
                "max_concurrency": 1,
                "timeout_seconds": 10,
            },
            "voices": [
                {
                    "id": "fake-es",
                    "locale": "es-MX",
                    "gender": "female",
                    "styles": [],
                }
            ],
        }
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        host, port = self._server.server_address
        return f"http://{host}:{port}"

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)

    def _handler(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args) -> None:
                return None

            def _send(self, status: int, payload: dict) -> None:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _authorized(self) -> bool:
                if outer.require_token is None:
                    return True
                if self.headers.get("X-Vibebook-Plugin-Token") == outer.require_token:
                    return True
                self._send(
                    401,
                    {"error": {"code": "unauthorized", "message": "Missing plugin token"}},
                )
                return False

            def do_GET(self) -> None:
                if not self._authorized():
                    return
                if self.path == "/v1/info":
                    self._send(200, outer.info)
                elif self.path == "/v1/health":
                    self._send(200, {"ok": True})
                elif self.path == "/v1/voices":
                    self._send(200, {"voices": outer.info["voices"]})
                else:
                    self._send(404, {"error": {"code": "not_found", "message": "No"}})

            def do_POST(self) -> None:
                if not self._authorized():
                    return
                if self.path != "/v1/synthesize":
                    self._send(404, {"error": {"code": "not_found", "message": "No"}})
                    return
                length = int(self.headers.get("Content-Length", "0"))
                request = json.loads(self.rfile.read(length) or b"{}")
                if outer.delay:
                    time.sleep(outer.delay)
                if outer.fail_synthesis:
                    self._send(
                        500,
                        {"error": {"code": "boom", "message": "Synthesis exploded"}},
                    )
                    return
                if outer.invalid_audio:
                    audio = b"not a wav"
                else:
                    buffer = io.BytesIO()
                    frames = 8820
                    with wave.open(buffer, "wb") as wav:
                        wav.setnchannels(1)
                        wav.setsampwidth(2)
                        wav.setframerate(22_050)
                        samples = (
                            int(8000 * math.sin(2 * math.pi * 220 * index / 22_050))
                            for index in range(frames)
                        )
                        wav.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))
                    audio = buffer.getvalue()
                self._send(
                    200,
                    {
                        "audio_base64": base64.b64encode(audio).decode("ascii"),
                        "format": "wav",
                        "duration_ms": 100,
                        "words": [],
                        "voice": request.get("voice"),
                    },
                )

        return Handler


@pytest.fixture
def plugin_server():
    server = FakePluginServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture
def make_plugin_server():
    servers: list[FakePluginServer] = []

    def factory(**kwargs):
        server = FakePluginServer(**kwargs)
        server.start()
        servers.append(server)
        return server

    yield factory
    for server in servers:
        server.stop()
