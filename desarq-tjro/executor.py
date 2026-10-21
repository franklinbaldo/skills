"""DESARQ offline ledger; no real POST until its contract is verified."""
import json
import sqlite3
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict, field_validator

class SelectionError(Exception): pass
class TransitionError(Exception): pass
class ReconciliationError(Exception): pass

class Volume(BaseModel):
    model_config=ConfigDict(extra="forbid", frozen=True)
    numero: str=Field(pattern=r"^(?:[0-9]{14}|[0-9]{20})$")
    id_processo: int=Field(gt=0)

class Selection(BaseModel):
    volumes: list[Volume]=Field(min_length=1)
    @field_validator("volumes")
    @classmethod
    def unique(cls, items):
        if len({(x.numero,x.id_processo) for x in items}) != len(items):
            raise ValueError("duplicate selected volume")
        return items

class Request(BaseModel):
    id: int=Field(gt=0)
    idProcesso: int=Field(gt=0)
    numeroProcesso: str

def reconcile(pages: list[dict], volume: Volume) -> int | None:
    """Only a full, consistent page collection may establish absence or identity."""
    if not pages:
        raise ReconciliationError("missing pages")
    try:
        total=pages[0]["page"]["totalPages"]
        numbers=[p["page"]["number"] for p in pages]
        if type(total) is not int or total < 1 or sorted(numbers)!=list(range(total)):
            raise ValueError("incomplete page set")
        if any(p["page"]["totalPages"]!=total for p in pages):
            raise ValueError("inconsistent pagination")
        matches={r.id for p in pages for raw in p["content"] for r in [Request.model_validate(raw)]
                 if r.numeroProcesso==volume.numero and r.idProcesso==volume.id_processo}
    except (ValueError,TypeError,KeyError) as exc:
        raise ReconciliationError("invalid/incomplete page set") from exc
    if len(matches)>1:
        raise ReconciliationError("ambiguous matching requests")
    return next(iter(matches)) if matches else None

class Ledger:
    """Persist intent BEFORE POST; never authorize an automatic retry."""
    def __init__(self, path):
        self.db=sqlite3.connect(path)
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS batches (id TEXT PRIMARY KEY, selection TEXT NOT NULL)")
        self.db.execute("""CREATE TABLE IF NOT EXISTS events
             (seq INTEGER PRIMARY KEY AUTOINCREMENT, batch TEXT NOT NULL, numero TEXT NOT NULL,
              volume_id INTEGER NOT NULL, state TEXT NOT NULL, request_id INTEGER, at TEXT NOT NULL)""")
        self.db.commit()
    def _event(self,batch,v,state,request_id=None):
        self.db.execute("INSERT INTO events(batch,numero,volume_id,state,request_id,at) VALUES (?,?,?,?,?,?)",
            (batch,v.numero,v.id_processo,state,request_id,datetime.now(timezone.utc).isoformat()))
    def create(self,batch,selection: Selection):
        try:
            with self.db:
                self.db.execute("INSERT INTO batches VALUES (?,?)",(batch,selection.model_dump_json()))
                for v in selection.volumes:self._event(batch,v,"selected")
        except sqlite3.IntegrityError as e:raise SelectionError("batch exists") from e
    def selection(self,batch):
        row=self.db.execute("SELECT selection FROM batches WHERE id=?",(batch,)).fetchone()
        if row is None:raise SelectionError("batch missing")
        return Selection.model_validate_json(row[0])
    def state(self,batch,v):
        row=self.db.execute("SELECT state FROM events WHERE batch=? AND numero=? AND volume_id=? ORDER BY seq DESC LIMIT 1",
                            (batch,v.numero,v.id_processo)).fetchone()
        if row is None:raise SelectionError("volume not selected")
        return row[0]
    def next(self,batch):
        for v in self.selection(batch).volumes:
            state=self.state(batch,v)
            if state=="confirmed":continue
            if state!="selected":raise TransitionError("blocked: "+state)
            return v
        return None
    def mark_post_possible(self,batch,v):
        """Call and commit BEFORE external side effect; never retry on timeout."""
        if self.next(batch)!=v:raise TransitionError("not next volume")
        with self.db:self._event(batch,v,"indeterminate")
    def confirm(self,batch,v,pages):
        if self.state(batch,v)!="indeterminate":raise TransitionError("not pending reconciliation")
        request_id=reconcile(pages,v)
        if request_id is None:raise ReconciliationError("not found; manual review required")
        with self.db:self._event(batch,v,"confirmed",request_id)
        return request_id
