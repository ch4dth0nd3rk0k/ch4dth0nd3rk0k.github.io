"""Tools for running Jekyll."""

import subprocess
from abc import ABC
from abc import abstractmethod
from functools import partial
from http.server import HTTPServer
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread
from typing import Any
from typing import Optional
from typing import Union


class BaseServer(ABC):
    """Abstract base class for different types of servers."""

    def __init__(self, host: str = "127.0.0.1", port: int = 4000) -> None:
        """Initialize the server."""
        self.host = host
        self.port = port

    @abstractmethod
    def start(self) -> None:
        """Start the server."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop the server."""
        pass

    def url(self) -> str:
        """Return the full URL of the running server."""
        return f"http://{self.host}:{self.port}/"


class CustomHTTPRequestHandler(SimpleHTTPRequestHandler):
    """Custom request handler to serve files from a specified directory."""

    def __init__(
        self, *args: Any, directory: Optional[str] = None, **kwargs: Any
    ) -> None:
        """Initialize the request handler with a specific directory."""
        super().__init__(*args, directory=directory, **kwargs)


class SimpleHTTPServer(BaseServer):
    """A lightweight HTTP server to serve static files from a directory."""

    def __init__(
        self, site_dir: Path, host: str = "127.0.0.1", port: int = 4000
    ) -> None:
        """Initialize the SimpleHTTPServer."""
        super().__init__(host, port)
        self.site_dir: Path = site_dir
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[Thread] = None

    def start(self) -> None:
        """Start the HTTP server in a separate thread."""
        handler = partial(
            CustomHTTPRequestHandler, directory=str(self.site_dir)
        )
        self.server = HTTPServer((self.host, self.port), handler)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        """Stop the HTTP server and wait for the thread to exit."""
        if self.server and self.thread:
            self.server.shutdown()
            self.thread.join()


class JekyllServer(BaseServer):
    """Manages a Jekyll server instance using subprocess."""

    def __init__(
        self,
        cwd: Union[Path, str],
        host: str = "127.0.0.1",
        port: int = 4000,
        source: Optional[str] = None,
    ) -> None:
        """Setup Jekyll server."""
        # call parents init method
        super().__init__(host, port)

        # instance specific setup
        self.cwd = Path(cwd)
        self.source = source
        self.process: Optional[subprocess.Popen[str]] = None

    def start(self) -> None:
        """Start the Jekyll server."""
        # check if current process running
        if self.process is not None:
            print(
                "Warning: Jekyll server is already running. "
                "Use `stop()` to stop the server before starting a new one."
            )

        # start new process
        else:
            # build command
            command = [
                "jekyll",
                "serve",
                "--host",
                self.host,
                "--port",
                str(self.port),
            ]

            # check optional src arg
            if self.source:
                command.extend(["--source", self.source])

            # start proc
            self.process = subprocess.Popen(
                command,
                cwd=self.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # notify
            print(
                f"Jekyll server started on "
                f"{self.host}:{self.port} with source={self.source}."
            )

    def stop(self) -> None:
        """Stop the Jekyll server."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.process.kill()

            print("Jekyll server stopped.")


def run_jekyll_build(
    site_dir: Path, destination: Optional[Path] = None
) -> subprocess.CompletedProcess[str]:
    """Runs `jekyll build` in the specified directory."""
    # build cmd
    cmd = ["jekyll", "build", "--source", str(site_dir)]

    # add optional destination
    if destination:
        cmd += ["--destination", str(destination)]

    # start process
    return subprocess.run(
        cmd,
        cwd=site_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
