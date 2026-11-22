"""
Custom (non-Toniebox) players: POST /api/registerDevice gives a self-built player its own overlay,
so it is listed by /api/getBoxes next to the Tonieboxes. See docs/custom-players.md.

    make test_py TESTS=register_device
"""

import http.client
import json
import os
from urllib.parse import quote, urlparse

BASE = urlparse(os.environ.get("TEDDYCLOUD_BASE_URL", "http://127.0.0.1:80"))


def request(method, path):
    conn = http.client.HTTPConnection(BASE.hostname, BASE.port, timeout=10)
    try:
        conn.request(method, path, headers={"Content-Length": "0"} if method == "POST" else {})
        resp = conn.getresponse()
        return resp.status, resp.read().decode(errors="replace")
    finally:
        conn.close()


def register(device_id, name=None, model=None):
    path = "/api/registerDevice?id=" + quote(device_id, safe="")
    if name is not None:
        path += "&name=" + quote(name, safe="")
    if model is not None:
        path += "&model=" + quote(model, safe="")
    return request("POST", path)


def boxes():
    status, body = request("GET", "/api/getBoxes")
    assert status == 200
    return {b["ID"]: b for b in json.loads(body)["boxes"]}


def test_register_lists_the_device():
    status, body = register("a1b2c3d4e5f6", "Kitchen player", "StoryPlayer")
    assert status == 200, body
    reply = json.loads(body)
    assert reply["ID"] == "a1b2c3d4e5f6"
    assert reply["boxName"] == "Kitchen player"
    assert reply["boxModel"] == "StoryPlayer"
    assert reply["created"] is True

    entry = boxes()["a1b2c3d4e5f6"]
    assert entry["custom"] is True
    assert entry["boxName"] == "Kitchen player"
    assert entry["boxModel"] == "StoryPlayer"
    assert entry["lastSeen"] > 0


def test_register_again_updates_instead_of_duplicating():
    assert register("0011223344aa", "First name", "v1")[0] == 200
    status, body = register("0011223344aa", "Second name", "v2")
    assert status == 200, body
    reply = json.loads(body)
    assert reply["created"] is False
    # the name belongs to the web UI once the player exists, the model follows the player
    assert reply["boxName"] == "First name"
    assert reply["boxModel"] == "v2"
    listed = [b for b in boxes().values() if b["commonName"].lower() == "0011223344aa"]
    assert len(listed) == 1

    # nothing given: both are kept
    status, body = register("0011223344aa")
    reply = json.loads(body)
    assert status == 200 and reply["boxName"] == "First name" and reply["boxModel"] == "v2"


def test_default_name():
    status, body = register("playerNoName")
    assert status == 200, body
    assert json.loads(body)["boxName"] == "Custom player playerNoName"


def test_invalid_ids_are_refused():
    for bad in ["", "abc", "x" * 16, "has space12", "semi;colon12", "../../etc/pw"]:
        status, _ = register(bad)
        assert status == 400, bad
    assert request("POST", "/api/registerDevice")[0] == 400
    for bad in ["abc", "x" * 16]:
        assert bad not in boxes()


def test_control_characters_do_not_reach_the_config():
    status, body = register("ctrlchars0001", "evil\r\noverlay.x.boxName=pwned", "m\todel")
    assert status == 200, body
    reply = json.loads(body)
    assert "\n" not in reply["boxName"] and "\r" not in reply["boxName"]
    assert reply["boxModel"] == "model"
    assert "x" not in boxes()


def test_device_overlay_is_usable():
    assert register("overlaydev001", "Overlay player")[0] == 200
    status, body = request("GET", "/api/getTagIndex?overlay=overlaydev001")
    assert status == 200, body
    assert "tags" in json.loads(body)
