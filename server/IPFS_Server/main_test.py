
import os
import pytest
from main import store, retrieve, gen_ifps_hash, add_doc, FileUpload
from utils import hexhash


def test_gen_ifps_hash():
	name = "file.txt"
	checksum = hexhash("somedata")
	assert gen_ifps_hash(name, checksum) == hexhash(f"{name}{checksum}")


def test_store_and_retrieve_success(tmp_path, monkeypatch):
	monkeypatch.chdir(tmp_path)
	(tmp_path / "store").mkdir()

	name = "file.txt"
	data = "hello world"
	checksum = hexhash(data)

	ifps = store(name, data, checksum)
	p = tmp_path / "store" / ifps
	assert p.exists()

	ret = retrieve(ifps)
	assert isinstance(ret, (bytes, bytearray))
	assert ret.decode() == data


def test_store_checksum_mismatch(tmp_path, monkeypatch):
	monkeypatch.chdir(tmp_path)
	(tmp_path / "store").mkdir()

	name = "file.txt"
	data = "good"
	checksum = hexhash(data)
	ifps = store(name, data, checksum)

	p = tmp_path / "store" / ifps
	# tamper file data to force checksum mismatch
	with open(p, "r+b") as f:
		f.readline()
		f.write(b"tampered")

	assert retrieve(ifps) == ""


def test_add_doc_endpoint(tmp_path, monkeypatch):
	monkeypatch.chdir(tmp_path)
	(tmp_path / "store").mkdir()

	data = "somedata"
	checksum = hexhash(data)
	req = FileUpload(checksum=checksum, data=data, name="a.txt")
	resp = add_doc(req)
	assert resp.status == 200
	assert resp.ifps_hash != ""

	bad = FileUpload(checksum="bad", data=data, name="b.txt")
	resp2 = add_doc(bad)
	assert resp2.status == 304

