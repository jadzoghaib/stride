"""Uploaded pictures and clips.

Files land on the local filesystem beside the database. That is a real
implementation rather than a stub — a post can carry a photograph the author
chose from their machine — and it is deliberately the *simplest* real one:
swapping it for object storage later means changing `_store` and `serve`, and
nothing that calls them.

What the endpoint refuses is the interesting part. Two rules do most of the
work:

**The client never names the file.** An upload is stored under a random name
with an extension this module chose from the declared type, so a request cannot
propose `../../etc/passwd`, `index.html`, or anything ending `.js` that a
browser would later execute from our origin.

**The declared type has to match what the bytes actually are.** A whitelist of
content types alone is a promise from whoever is uploading; sniffing the first
few bytes checks it. A PNG header is a PNG header regardless of what the form
said, and an HTML file claiming to be an image stops here.
"""

from __future__ import annotations

import re
import secrets

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..auth import require_role
from ..config import settings

router = APIRouter(prefix="/api", tags=["media"])

#: What we accept, and what we will call it on disk. Extensions come from here
#: rather than from the uploaded filename, so the set of things that can exist
#: in the media directory is closed.
ACCEPTED = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
}

#: The first bytes each format starts with. `None` means we have no cheap
#: signature for it and accept the declared type -- both video containers put
#: their marker at a variable offset, and reading far enough to find it is not
#: worth it for a demo. They are still inside the whitelist above.
MAGIC: dict[str, tuple[bytes, ...] | None] = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/gif": (b"GIF87a", b"GIF89a"),
    "image/webp": (b"RIFF",),
    "video/mp4": None,
    "video/webm": (b"\x1a\x45\xdf\xa3",),
}

#: A stored name is a token and an extension. Anything else is not ours, and is
#: never opened -- this is what keeps a request from walking out of the media
#: directory with a crafted path.
STORED_NAME = re.compile(r"^[A-Za-z0-9_-]{16,64}\.(jpg|png|webp|gif|mp4|webm)$")


@router.post("/media", status_code=201)
async def upload(file: UploadFile = File(...),
                 _: dict = Depends(require_role("athlete", "club"))):
    if file.content_type not in ACCEPTED:
        raise HTTPException(422, "unsupported_media_type")

    # Read with the ceiling in hand. `content-length` is checked by the
    # middleware, but a chunked upload has no length to check, so the only
    # honest limit is the one applied while reading.
    payload = await file.read(settings.max_upload_bytes + 1)
    if len(payload) > settings.max_upload_bytes:
        raise HTTPException(413, "payload_too_large")
    if not payload:
        raise HTTPException(422, "empty_file")

    signatures = MAGIC.get(file.content_type)
    if signatures and not any(payload.startswith(sig) for sig in signatures):
        # The form said one thing and the bytes say another. Refusing here is
        # what stops an HTML file arriving as "image/png" and being served back
        # from our own origin.
        raise HTTPException(422, "content_does_not_match_its_type")

    name = f"{secrets.token_urlsafe(18)}{ACCEPTED[file.content_type]}"
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    (settings.media_dir / name).write_bytes(payload)

    kind = "video" if file.content_type.startswith("video/") else "image"
    return {"media_url": f"/api/media/{name}", "media_kind": kind, "bytes": len(payload)}


@router.get("/media/{name}")
def serve(name: str):
    """Public: this is what a post's picture points at.

    The name is matched against the pattern we generate rather than sanitised.
    Sanitising is a list of things to remove and is only ever as good as the
    list; matching is a description of what is allowed, and `..` is not in it.
    """
    if not STORED_NAME.match(name):
        raise HTTPException(404, "unknown_media")
    path = settings.media_dir / name
    if not path.is_file():
        raise HTTPException(404, "unknown_media")
    return FileResponse(path)
