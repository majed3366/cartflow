"""Same process as: python -m uvicorn main:app --host 0.0.0.0 --port <PORT> (PORT from env, default 8000)."""

import os
import sys


def main() -> None:
    port = os.environ.get("PORT", "8000")
    os.execvp(
        sys.executable,
        [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--host",
            "0.0.0.0",
            "--port",
            port,
        ],
    )


if __name__ == "__main__":
    main()
