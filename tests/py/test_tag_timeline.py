"""
Picture timeline of a tag: a "<name>.timeline.json" next to the TAF a tag plays is served by
/api/getTagTimeline with a download URL per picture, and announced as tagInfo.timelineUrl.
See docs/api/tag-timeline.md.

    make test_py TESTS=tag_timeline
"""

import http.client
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sim import taf  # noqa: E402

BASE = urlparse(os.environ.get("TEDDYCLOUD_BASE_URL", "http://127.0.0.1:80"))
SANDBOX = os.environ.get("TC_SANDBOX")

pytestmark = pytest.mark.skipif(not SANDBOX, reason="needs the sandbox from tests/py/with_server.sh")

RUID = "a1b2c3d4500304e0"
PLAIN = "a1b2c3d5500304e0"  # a tag whose book has no timeline
JPEG = b"\xff\xd8\xff\xe0" + os.urandom(900) + b"\xff\xd9"


def api(method, path, body=None):
    conn = http.client.HTTPConnection(BASE.hostname, BASE.port, timeout=20)
    try:
        conn.request(method, path, body)
        resp = conn.getresponse()
        return resp.status, resp.read()
    finally:
        conn.close()


def library():
    return Path(SANDBOX) / "data" / "library"


def assign(ruid, source):
    # the first content request creates the tag, then it gets its source
    api("GET", f"/content/download/{ruid[:8].upper()}/{ruid[8:].upper()}")
    status, body = api("POST", f"/content/json/set/{ruid}", f"source={source}&nocloud=true")
    assert status == 200, body


def tag_info(ruid):
    status, body = api("GET", f"/api/getTagInfo?ruid={ruid}")
    assert status == 200, body
    return json.loads(body)["tagInfo"]


@pytest.fixture(scope="module", autouse=True)
def book():
    make_book()


def make_book():
    folder = library() / "Little Red"
    (folder / "pics").mkdir(parents=True, exist_ok=True)
    (folder / "story.taf").write_bytes(taf.build(77001, os.urandom(32 * 1024)))
    (folder / "plain.taf").write_bytes(taf.build(77002, os.urandom(32 * 1024)))
    (folder / "forest.jpg").write_bytes(JPEG)
    (folder / "pics" / "big wolf.jpg").write_bytes(JPEG + b"more")
    (folder / "story.timeline.json").write_text(
        json.dumps(
            {
                "images": [
                    {"track": 1, "at": "0:20", "image": "forest.jpg"},
                    {"track": 1, "at": 95, "image": "pics/big wolf.jpg"},
                    {"at": "1:02:03", "image": "gone.jpg"},
                    {"track": 2, "at": 0, "image": "../../config/config.ini"},
                    {"track": 2, "at": 0, "image": "/etc/passwd"},
                    {"track": 2, "at": 0},
                ]
            }
        )
    )
    assign(RUID, "lib://Little Red/story.taf")
    assign(PLAIN, "lib://Little Red/plain.taf")


def test_tag_info_announces_the_timeline():
    assert tag_info(RUID)["timelineUrl"].startswith(f"/api/getTagTimeline?ruid={RUID}")
    assert "timelineUrl" not in tag_info(PLAIN)


def test_timeline_lists_pictures_with_urls():
    status, body = api("GET", tag_info(RUID)["timelineUrl"])
    assert status == 200, body
    reply = json.loads(body)
    assert reply["ruid"] == RUID
    images = reply["images"]
    # entries that leave the folder or name no picture are dropped
    assert [i["image"] for i in images] == ["forest.jpg", "pics/big wolf.jpg", "gone.jpg"]

    assert images[0]["track"] == 1 and images[0]["at"] == "0:20"
    assert images[0]["size"] == len(JPEG)
    assert images[1]["at"] == 95 and images[1]["size"] == len(JPEG) + 4
    # a picture that is not on the server has no url, and no track means book time
    assert "url" not in images[2] and "track" not in images[2] and images[2]["at"] == "1:02:03"


def test_picture_urls_download_the_files():
    images = json.loads(api("GET", f"/api/getTagTimeline?ruid={RUID}")[1])["images"]
    status, body = api("GET", images[0]["url"])
    assert status == 200 and body == JPEG
    assert " " not in images[1]["url"]
    status, body = api("GET", images[1]["url"])
    assert status == 200 and body == JPEG + b"more"


def test_no_timeline_is_not_found():
    assert api("GET", f"/api/getTagTimeline?ruid={PLAIN}")[0] == 404
    assert api("GET", "/api/getTagTimeline?ruid=ffffffffffffffff")[0] == 404
    assert api("GET", "/api/getTagTimeline?ruid=nonsense")[0] == 404
    assert api("GET", "/api/getTagTimeline")[0] == 404


def test_broken_timeline_is_not_found():
    path = library() / "Little Red" / "story.timeline.json"
    good = path.read_text()
    try:
        path.write_text("{ not json")
        assert api("GET", f"/api/getTagTimeline?ruid={RUID}")[0] == 404
        path.write_text('{"images": "nope"}')
        assert api("GET", f"/api/getTagTimeline?ruid={RUID}")[0] == 404
    finally:
        path.write_text(good)
    assert api("GET", f"/api/getTagTimeline?ruid={RUID}")[0] == 200
