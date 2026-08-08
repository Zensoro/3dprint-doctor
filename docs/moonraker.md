# Klipper / Moonraker

Print Doctor's `watch` command monitors a Moonraker webcam snapshot URL
directly — no plugin needed.

## Find your webcam snapshot URL

Moonraker exposes webcams at:

```
http://<host>:7125/server/webcams/snapshot?name=<webcam_name>
```

On Mainsail/Fluidd this is usually `webcam`:

```bash
curl http://your-printer:7125/server/webcams/snapshot?name=webcam -o frame.jpg
file frame.jpg   # -> JPEG image data
```

Legacy webcam config is often `http://<host>:8080/webcam/?action=snapshot`.

## Monitor it

```bash
print-doctor watch "http://your-printer:7125/server/webcams/snapshot?name=webcam" \
  -i 5 -e ./evidence -w http://notify.example.com/alert
```

Alerts fire on defects: evidence screenshot saved, console printed, optional
webhook POST (JSON).

## Stop on defect via Moonraker API

The webhook can POST to Moonraker to pause/stop:

```bash
curl -X POST http://your-printer:7125/printer/print/pause \
  -H "X-Api-Key: <moonraker_api_key>"
```

## Basic auth

```bash
print-doctor watch "https://your-printer:7125/server/webcams/snapshot?name=webcam" \
  -u <user> -P <password> -i 5
```
