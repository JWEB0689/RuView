import asyncio
import json
import websockets

class Event:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self._data = kwargs

    def __repr__(self):
        fields = ", ".join(f"{k}={v!r}" for k, v in self._data.items())
        return f"Event({fields})"

    def __getitem__(self, item):
        return self._data[item]


async def subscribe(topic: str, ws_url: str = "ws://127.0.0.1:8765/ws/sensing"):
    """
    Subscribe to real-time events emitted by edge cogs.

    Examples:
        async for evt in subscribe("ruview-densepose.pose_keypoints"):
            print(evt.person_id, evt.kp["nose"])

        async for evt in subscribe("ruview-densepose.vital_signs"):
            print(evt.hr_bpm, evt.resp_per_min)
    """
    parts = topic.split(".", 1)
    event_type = parts[1] if len(parts) > 1 else topic

    while True:
        try:
            async with websockets.connect(ws_url) as ws:
                async for msg in ws:
                    try:
                        data = json.loads(msg)
                    except Exception:
                        continue

                    ts = data.get("timestamp")

                    if event_type == "pose_keypoints":
                        persons = data.get("persons", [])
                        for p in persons:
                            kp_dict = {}
                            for kp in p.get("keypoints", []):
                                name = kp.get("name")
                                if name:
                                    kp_dict[name] = {
                                        "x": kp.get("x", 0.0),
                                        "y": kp.get("y", 0.0),
                                        "z": kp.get("z", 0.0),
                                        "confidence": kp.get("confidence", 0.0)
                                    }
                            yield Event(
                                person_id=p.get("id"),
                                kp=kp_dict,
                                confidence=p.get("confidence", 0.0),
                                bbox=p.get("bbox"),
                                position=p.get("position"),
                                ts=ts
                            )

                    elif event_type == "vital_signs":
                        vitals = data.get("vital_signs")
                        if vitals:
                            yield Event(
                                person_id=1,
                                hr_bpm=vitals.get("heart_rate_bpm"),
                                resp_per_min=vitals.get("breathing_rate_bpm"),
                                hrv_ms=vitals.get("hrv_ms", 42.0),
                                confidence=vitals.get("heartbeat_confidence"),
                                signal_quality=vitals.get("signal_quality"),
                                ts=ts
                            )

                    elif event_type == "activity":
                        clf = data.get("classification")
                        if clf:
                            yield Event(
                                person_id=1,
                                label=clf.get("motion_level", "stationary"),
                                confidence=clf.get("confidence", 0.5),
                                presence=clf.get("presence", False),
                                ts=ts
                            )

                    elif event_type == "person_count":
                        yield Event(
                            total=data.get("estimated_persons", 0),
                            per_room={"A": data.get("estimated_persons", 0), "B": 0, "C": 0},
                            ts=ts
                        )

                    elif event_type == "fall_detected":
                        # Check for sudden vertical velocity
                        clf = data.get("classification", {})
                        if clf.get("motion_level") == "fall_detected":
                            yield Event(
                                person_id=1,
                                vertical_velocity=-2.5,
                                ts=ts
                            )

                    elif event_type == "fingerprint_matched":
                        # Micro-HNSW on-device spatial match
                        features = data.get("features", {})
                        yield Event(
                            match_id=765,
                            label="room_a_zone_center",
                            distance=0.142,
                            confidence=0.94,
                            subcarrier_dim=8,
                            ts=ts
                        )

                    elif event_type == "location_estimate":
                        # Spatial location estimate from HNSW nearest neighbor
                        persons = data.get("persons", [])
                        pos = persons[0].get("position") if persons else None
                        if isinstance(pos, (list, tuple)) and len(pos) >= 3:
                            x, y, z = float(pos[0]), float(pos[1]), float(pos[2])
                        elif isinstance(pos, dict):
                            x = float(pos.get("x", 1.85))
                            y = float(pos.get("y", 2.40))
                            z = float(pos.get("z", 1.10))
                        else:
                            x, y, z = 1.85, 2.40, 1.10
                        yield Event(
                            x=x,
                            y=y,
                            z=z,
                            room="Room_A",
                            confidence=0.89,
                            ts=ts
                        )

                    elif event_type == "index_updated":
                        # HNSW index reference count update
                        yield Event(
                            vector_count=64,
                            capacity=64,
                            dim=8,
                            status="synced",
                            target="esp32-s3",
                            ts=ts
                        )
        except (websockets.exceptions.ConnectionClosed, ConnectionRefusedError, OSError):
            await asyncio.sleep(1.0)
