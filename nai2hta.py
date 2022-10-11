from __future__ import annotations

import contextlib
import glob
import json
import re
import sqlite3
import sys
from collections.abc import Iterable
from pathlib import Path

from PIL import Image

WS = re.compile(r"\s+")


## Matches the Hydrus Tag Archive schema
HTA_SCHEMA = """
    BEGIN;
    CREATE TABLE hash_type ( hash_type INTEGER );

    CREATE TABLE hashes ( hash_id INTEGER PRIMARY KEY, hash BLOB_BYTES );
    CREATE UNIQUE INDEX hashes_hash_index ON hashes ( hash );

    CREATE TABLE mappings ( hash_id INTEGER, tag_id INTEGER, PRIMARY KEY ( hash_id, tag_id ) );
    CREATE INDEX mappings_hash_id_index ON mappings ( hash_id );

    CREATE TABLE namespaces ( namespace TEXT );

    CREATE TABLE tags ( tag_id INTEGER PRIMARY KEY, tag TEXT );
    CREATE UNIQUE INDEX tags_tag_index ON tags ( tag );

    INSERT INTO hash_type (hash_type) VALUES (2);
    COMMIT;
"""


class HTA:
    _conn: sqlite3.Connection

    _namespaces: set[str]

    _tags: dict[str, int]

    _last_hash_id: int
    _last_tag_id: int

    def __init__(self, path: Path | str) -> None:
        self._conn = sqlite3.connect(path)
        self._tags = {}
        self._last_tag_id = 0
        self._last_hash_id = 0
        self._load()

    def _load(self) -> None:
        with contextlib.closing(self._conn.cursor()) as cur:
            try:
                cur.execute("SELECT hash_type FROM hash_type")
                hash_type = cur.fetchone()[0]
                assert hash_type == 2
            except:
                cur.executescript(HTA_SCHEMA)

            cur.execute("SELECT namespace FROM namespaces")
            self._namespaces = {row[0] for row in cur}

            cur.execute("SELECT MAX(hash_id) FROM hashes")
            self._last_hash_id = cur.fetchone()[0] or 0

            cur.execute("SELECT MAX(tag_id) FROM tags")
            self._last_tag_id = cur.fetchone()[0] or 0

    def _ensure_hash(self, file_hash: str) -> int:
        hash_bytes = bytes.fromhex(file_hash)

        with contextlib.closing(self._conn.cursor()) as cur:
            cur.execute("SELECT hash_id FROM hashes WHERE hash = ?", (hash_bytes,))
            if (row := cur.fetchone()) is not None:
                return row[0]

            hash_id = self._last_hash_id + 1
            cur.execute(
                "INSERT INTO hashes (hash_id, hash) VALUES (?, ?)",
                (hash_id, hash_bytes),
            )
            cur.connection.commit()
            self._last_hash_id = hash_id
            return hash_id

    def _ensure_tag(self, tag: str | tuple[str, str]) -> int:
        if isinstance(tag, tuple):
            ns, tag = tag
        else:
            ns = None

        with contextlib.closing(self._conn.cursor()) as cur:
            if ns is not None:
                if ns not in self._namespaces:
                    cur.execute("INSERT INTO namespaces (namespace) VALUES (?)", (ns,))
                    cur.connection.commit()
                    self._namespaces.add(ns)
                tag = f"{ns}:{tag}"

            if (cached := self._tags.get(tag)) is not None:
                return cached

            cur.execute("SELECT tag_id FROM tags WHERE tag = ?", (tag,))
            if (row := cur.fetchone()) is not None:
                self._tags[tag] = row[0]
                return row[0]

            tag_id = self._last_tag_id + 1
            cur.execute("INSERT INTO tags (tag_id, tag) VALUES (?, ?)", (tag_id, tag))
            cur.connection.commit()
            self._last_tag_id = tag_id
            return tag_id

    def add_tags(self, file_hash: str, tags: set[str | tuple[str, str]]) -> None:
        hash_id = self._ensure_hash(file_hash)
        mappings = {(hash_id, self._ensure_tag(t)) for t in tags}
        with contextlib.closing(self._conn.cursor()) as cur:
            cur.executemany("INSERT OR IGNORE INTO mappings VALUES (?, ?)", mappings)
            cur.connection.commit()

    def close(self) -> None:
        self._conn.commit()
        self._conn.close()


def parse_tags(tags: str) -> Iterable[str]:
    for mixing in WS.sub(" ", tags).split("|"):
        for tag in mixing.split(","):
            if ":" in tag:
                tag = tag.split(":", 1)[0]
            if tag := tag.strip("{}[], ").lower():
                yield tag


def derive_tags(image_path: Path | str) -> set[str | tuple[str, str]] | None:
    try:
        with contextlib.closing(Image.open(image_path)) as im:
            if im.info.get("Software") != "NovelAI":
                return None

            tags: set[str | tuple[str, str]] = set(parse_tags(im.info["Description"]))
            tags.add(("model", im.info["Source"].split(" ")[-1].lower()))

            params = json.loads(im.info["Comment"])
            for param in ("steps", "sampler", "seed", "scale"):
                tags.add((param, str(params[param]).lower()))

            return tags
    except Exception as ex:
        print(ex)
        pass
    return None


def main(db_path: Path | str, hta_path: Path | str) -> None:
    with contextlib.closing(HTA(hta_path)) as hta:
        for path in glob.iglob("client_files/f*/*.png", root_dir=db_path):
            file_hash = Path(path).stem
            if tags := derive_tags(Path(db_path) / path):
                print(f"{file_hash}: adding {len(tags)} tag(s)")
                hta.add_tags(file_hash, tags)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
