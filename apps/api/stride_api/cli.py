"""CLI: init / reset / serve. Usual path: uv run stride serve"""

from __future__ import annotations

import argparse
import sys

from .config import settings
from .db import connect, drop_all, init_db


def _where() -> str:
    return f"postgres ({settings.database_url.rsplit('@', 1)[-1]})" \
        if settings.db_backend == "postgres" else str(settings.db_path)


def cmd_init(_args) -> int:
    from .seed import is_seeded, seed
    conn = connect()
    init_db(conn)
    if is_seeded(conn):
        print(f"already initialized: {_where()}")
        return 0
    print(f"initialized {_where()}: {seed(conn)}")
    return 0


def cmd_reset(args) -> int:
    if settings.db_backend == "postgres":
        conn = connect()
        drop_all(conn)
        conn.close()
        print(f"dropped Stride tables in {_where()}")
    elif settings.db_path.exists():
        settings.db_path.unlink()
        print(f"deleted {settings.db_path}")
    return cmd_init(args)


def cmd_serve(args) -> int:
    import uvicorn
    cmd_init(args)
    uvicorn.run("stride_api.main:app", host=args.host, port=args.port)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="stride")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="create + seed the database (idempotent)")
    sub.add_parser("reset", help="wipe and re-seed")
    p_serve = sub.add_parser("serve", help="run the API")
    p_serve.add_argument("--port", type=int, default=8490)
    p_serve.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    return {"init": cmd_init, "reset": cmd_reset, "serve": cmd_serve}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
