# Custom players API

A *custom player* is a self-built device that plays TeddyCloud content but is not a
Toniebox: it has no box certificate and never uses the box protocol on port 443. It
only talks to the web API, the same one the web UI uses.

`POST /api/registerDevice` lets such a player announce itself. It then gets its own
settings overlay, exactly like a Toniebox does on its first connection, so it

- is listed by `GET /api/getBoxes` (and therefore in the web UI) next to the boxes,
- can be given its own settings (content directory, ...) through the overlay, and
- can be removed again with `POST /api/settings/removeOverlay?overlay=<ID>`.

## Register

```
POST /api/registerDevice?id=<id>[&name=<text>][&model=<text>]
```

| Parameter | |
| --- | --- |
| `id` | Required. A stable ID of the device, 6-15 characters of `A-Z a-z 0-9 _ -`. The MAC address without colons (12 hex digits) is a good choice, it is what Tonieboxes use. |
| `name` | Optional display name, up to 64 characters. Default: `Custom player <id>`. |
| `model` | Optional model text, up to 32 characters, e.g. the project name. |

Control characters are dropped from `name` and `model`.

The call is idempotent: a player calls it whenever it connects. The first call creates
the overlay; later calls refresh the last-seen time and IP, and update the name or model
when one is given and differs from the stored one. A name changed in the web UI is
therefore only kept if the player stops sending `name`.

Response `200`, `text/json`:

```json
{ "ID": "a1b2c3d4e5f6", "commonName": "a1b2c3d4e5f6", "boxName": "Kitchen player",
  "boxModel": "StoryPlayer", "boxVersion": 5, "created": true }
```

`ID` is the overlay ID to pass as `overlay=<ID>` to other API calls. `boxVersion` 5 is
`BOX_CUSTOM`.

Errors, `text/plain`:

| Status | |
| --- | --- |
| `400` | `id` is missing, too long or contains other characters. |
| `409` | The ID belongs to a Toniebox, or all overlay slots (`MAX_OVERLAYS`) are in use. |

If the web UI login is enabled, the player logs in like any other API client first.

## What `getBoxes` reports

Every entry of `GET /api/getBoxes` has two more fields:

| Field | |
| --- | --- |
| `custom` | `true` for a registered custom player, `false` for a Toniebox. |
| `lastSeen` | Unix time of the last connection (box) or registration (custom player) since the server started, `0` if none. |

## Playing a tag

Nothing here is specific to custom players; these are the existing endpoints, listed as
the minimum a player needs. `ruid` is the tag UID as 16 lowercase hex digits in the
order the bytes arrive over the air (`e0` last for ISO 15693).

1. `GET /api/getTagInfo?ruid=<ruid>[&overlay=<ID>]` - what the tag plays. The reply
   has a `tagInfo` object with, among others, `valid`, `exists`, `live`, `source`,
   `trackSeconds`, `lengthSeconds`, `audioUrl` and a `tonieInfo` object (`series`,
   `episode`, `picture`, `tracks`).
2. `GET /content/download/<ruid 0-7>/<ruid 8-15>[?overlay=<ID>]` - the TAF file, both
   path parts in upper case as in the content directory. `Range` requests are
   supported, so a player can resume a download and start playing before the file is
   complete. `audioUrl` from step 1 is the same URL with `skip_header=true`, i.e. the
   plain Ogg Opus stream without the TAF header.

The TAF format (4096-byte protobuf header, then Ogg Opus) is described in
[architecture.md](../architecture.md#tonie--taf-content-model).
