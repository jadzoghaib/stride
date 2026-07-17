"""CLI: init / reset / serve / sync / score.

Usual path:  uv run creatorlens serve   (auto-inits + seeds on first run)
"""

from __future__ import annotations

import argparse
import sys

from .db import connect, db_path, init_db


def cmd_init(_args) -> int:
    from .seed import is_seeded, seed
    conn = connect()
    init_db(conn)
    if is_seeded(conn):
        print(f"already initialized: {db_path()}")
        return 0
    summary = seed(conn)
    print(f"initialized {db_path()}: {summary}")
    return 0


def cmd_reset(_args) -> int:
    path = db_path()
    if path.exists():
        path.unlink()
        print(f"deleted {path}")
    return cmd_init(_args)


def cmd_serve(args) -> int:
    import uvicorn
    cmd_init(args)  # ensure db exists + seeded before serving
    uvicorn.run("creatorlens.api.main:app", host="127.0.0.1", port=args.port)
    return 0


def cmd_sync(args) -> int:
    from .ingestion import sync_account, sync_all
    conn = connect()
    if args.account:
        results = [sync_account(conn, args.account, trigger="manual")]
    else:
        results = sync_all(conn, trigger="scheduled")
    for r in results:
        print(r)
    return 0


def cmd_score(args) -> int:
    from .analytics.scoring import InsufficientData, store_scores
    from .db import rows
    conn = connect()
    creator_ids = [args.creator] if args.creator else [r["id"] for r in rows(conn, "SELECT id FROM creators")]
    for cid in creator_ids:
        try:
            result = store_scores(conn, cid, target_id=args.target, actor="user")
            print(cid, result["dimensions"])
        except InsufficientData as exc:
            print(cid, f"skipped: {exc.reason}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="creatorlens")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="create the database and seed it (idempotent)")
    sub.add_parser("reset", help="delete the database and re-seed")

    p_serve = sub.add_parser("serve", help="run the API + console")
    p_serve.add_argument("--port", type=int, default=8477)

    p_sync = sub.add_parser("sync", help="run the ingestion pipeline")
    p_sync.add_argument("--account", type=int, help="one account id (default: all connected)")

    p_score = sub.add_parser("score", help="recompute marketability scores")
    p_score.add_argument("--creator", type=int, help="one creator id (default: all)")
    p_score.add_argument("--target", type=int, default=1, help="sponsor target id (default 1)")

    args = parser.parse_args()
    return {"init": cmd_init, "reset": cmd_reset, "serve": cmd_serve,
            "sync": cmd_sync, "score": cmd_score}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
