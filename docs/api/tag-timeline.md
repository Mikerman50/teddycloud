# Tag timeline API

A *timeline* lists pictures that belong to moments of a story, so a player with a
screen can show them while the audio plays. TeddyCloud only stores and serves it; a
Toniebox ignores it.

## The sidecar file

The timeline is a JSON file next to the TAF, named like it with `.timeline.json`
instead of `.taf`:

```
library/Little Red/story.taf
library/Little Red/story.timeline.json
library/Little Red/forest.jpg
library/Little Red/pics/wolf.jpg
```

```json
{ "images": [
    { "track": 1, "at": "0:20", "image": "forest.jpg" },
    { "track": 1, "at": 95,     "image": "pics/wolf.jpg" },
    { "at": "1:02:03",          "image": "forest.jpg" }
] }
```

| Field | |
| --- | --- |
| `image` | Required. Path of the picture, relative to the folder of the TAF. It cannot leave that folder. |
| `at` | When the picture appears: seconds as a number, or `"m:ss"` / `"h:mm:ss"`. Default 0. |
| `track` | Optional track (chapter) number, 1 = first. `at` then counts from the start of that track, otherwise from the start of the audio. |

Entries are in story order. Because the file belongs to the TAF, every tag that plays
that TAF (`lib://` source) has the timeline; a TAF stored in a tag's own content folder
can have one in the same way. Upload the files like any other library file. Up to 64 KiB
and 200 entries are served.

## GET /api/getTagTimeline

```
GET /api/getTagTimeline?ruid=<ruid>[&overlay=<ID>]
```

Returns the timeline of the TAF the tag plays, with a download URL per picture:

```json
{ "ruid": "a1b2c3d4500304e0",
  "images": [
    { "track": 1, "at": "0:20", "image": "forest.jpg",
      "url": "/content/Little%20Red/forest.jpg?special=library", "size": 48213 },
    { "track": 1, "at": 95, "image": "pics/wolf.jpg",
      "url": "/content/Little%20Red/pics/wolf.jpg?special=library", "size": 51877 }
] }
```

- `track`, `at` and `image` are passed through as written.
- `url` and `size` (bytes) are present when the picture exists on the server. A client
  can compare `size` with its cached copy to see whether it has to download again.
- Entries without a usable `image` are dropped.

`404` if the tag is unknown, plays no local TAF (stream, playlist) or the TAF has no
valid timeline file.

## tagInfo.timelineUrl

`GET /api/getTagInfo` and `GET /api/getTagIndex` report `timelineUrl` in a tag's
`tagInfo` when its TAF has a timeline file, so a client needs no extra request to find
out. The field is absent otherwise.
