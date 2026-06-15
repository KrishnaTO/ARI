"""File-backed feedback log for disease-data terms.

Feedback comments are stored as structured log entries in ``feedback/feedback.json``
(plus an append-only ``feedback/feedback.log`` audit trail). Each entry is tied to a
disease term. By default an entry lives only until the next version release, at which
point it is moved into ``feedback/archive/``; entries flagged ``keep`` survive releases.
"""
import json
import uuid
from datetime import datetime
from pathlib import Path


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


class FeedbackStore:
    def __init__(self, base_dir):
        self.dir = Path(base_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "feedback.json"
        self.log_path = self.dir / "feedback.log"
        self.archive_dir = self.dir / "archive"

    # ------------------------------------------------------------------ io
    def _load(self) -> list:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return []
        return []

    def _save(self, items: list):
        self.path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")

    def _log(self, action: str, entry: dict):
        line = (f"{_now()} | {entry.get('author', '')} | {action} | "
                f"term={entry.get('term', '')} | keep={entry.get('keep')} | "
                f"{entry.get('message', '')}\n")
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line)

    # ----------------------------------------------------------------- api
    def list(self, disease_iri: str = None) -> list:
        items = self._load()
        if disease_iri:
            items = [x for x in items if x.get("disease_iri") == disease_iri]
        return sorted(items, key=lambda x: x.get("created", ""))

    def add(self, disease_iri: str, term: str, message: str,
            keep: bool = False, author: str = "anonymous") -> dict:
        message = (message or "").strip()
        if not message:
            raise ValueError("Feedback message is empty")
        items = self._load()
        entry = {
            "id": "fb_" + uuid.uuid4().hex[:10],
            "disease_iri": disease_iri,
            "term": term,
            "message": message,
            "keep": bool(keep),
            "author": (author or "anonymous").strip() or "anonymous",
            "created": _now(),
            "updated": _now(),
        }
        items.append(entry)
        self._save(items)
        self._log("ADD", entry)
        return entry

    def update(self, fid: str, message=None, keep=None, author=None) -> dict:
        items = self._load()
        found = None
        for x in items:
            if x.get("id") == fid:
                if message is not None:
                    x["message"] = str(message).strip()
                if keep is not None:
                    x["keep"] = bool(keep)
                if author:
                    x["author"] = str(author).strip()
                x["updated"] = _now()
                found = x
                break
        if found is None:
            raise KeyError(fid)
        self._save(items)
        self._log("EDIT", found)
        return found

    def delete(self, fid: str) -> dict:
        items = self._load()
        removed = next((x for x in items if x.get("id") == fid), None)
        if removed:
            self._log("DELETE", removed)
        self._save([x for x in items if x.get("id") != fid])
        return {"ok": True, "deleted": bool(removed)}

    def archive_on_release(self, version: str) -> dict:
        """Move non-kept feedback into a versioned archive; retain flagged entries."""
        items = self._load()
        expiring = [x for x in items if not x.get("keep")]
        retained = [x for x in items if x.get("keep")]
        if expiring:
            self.archive_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = self.archive_dir / f"feedback_v{version}_{ts}.json"
            dest.write_text(json.dumps(expiring, indent=2, ensure_ascii=False), encoding="utf-8")
            with open(self.log_path, "a", encoding="utf-8") as f:
                for x in expiring:
                    f.write(f"{_now()} | system | ARCHIVED@v{version} | "
                            f"term={x.get('term', '')} | {x.get('message', '')}\n")
        self._save(retained)
        return {"archived": len(expiring), "retained": len(retained)}
