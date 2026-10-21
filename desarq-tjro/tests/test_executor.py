"""Run: uv run --with pydantic --with pytest pytest -q desarq-tjro/tests"""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from pydantic import ValidationError
from executor import Volume,Selection,Ledger,SelectionError,TransitionError,ReconciliationError,reconcile
N="12345678901234"
def v(i=1):return Volume(numero=N,id_processo=i)
def req(i=1,rid=99):return {"id":rid,"idProcesso":i,"numeroProcesso":N}
def page(items,n=0,total=1):return {"content":items,"page":{"number":n,"totalPages":total}}
def test_duplicate_selection():
    with pytest.raises(ValidationError):Selection(volumes=[v(),v()])
def test_volume_not_skipped(tmp_path):
    l=Ledger(str(tmp_path/"ledger.db"));l.create("x",Selection(volumes=[v(1),v(2)]))
    assert l.next("x")==v(1)
    l.mark_post_possible("x",v(1))
    with pytest.raises(TransitionError):l.next("x")
    l.confirm("x",v(1),[page([req(1)])])
    assert l.next("x")==v(2)
def test_restart_never_retries(tmp_path):
    path=str(tmp_path/"ledger.db")
    l=Ledger(path);l.create("x",Selection(volumes=[v()]))
    l.mark_post_possible("x",v())
    with pytest.raises(TransitionError):Ledger(path).mark_post_possible("x",v())
def test_missing_page_fails():
    with pytest.raises(ReconciliationError):reconcile([page([],0,2)],v())
def test_second_page():
    assert reconcile([page([],0,2),page([req()],1,2)],v())==99
def test_ambiguous():
    with pytest.raises(ReconciliationError):reconcile([page([req(rid=1),req(rid=2)])],v())
def test_wrong_volume_no_confirmation(tmp_path):
    l=Ledger(str(tmp_path/"ledger.db"));l.create("x",Selection(volumes=[v()]))
    l.mark_post_possible("x",v())
    with pytest.raises(ReconciliationError):l.confirm("x",v(),[page([req(2)])])
def test_unsolicited_volume(tmp_path):
    l=Ledger(str(tmp_path/"ledger.db"));l.create("x",Selection(volumes=[v()]))
    with pytest.raises(TransitionError):l.mark_post_possible("x",v(2))
