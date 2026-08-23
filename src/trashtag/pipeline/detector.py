"""Deterministic stub detector for the processing pipeline (§2.2).

This is a stand-in for a fine-tuned YOLO/ONNX detector (architecture §4). It derives all
detections from a hash of the media bytes so the pipeline is testable without a GPU — same
bytes + coords → same detections, always.

Swap in a real model behind the same `Detector` Protocol signature when ready.
"""

import hashlib
import os

from trashtag.pipeline.models import IssueClass, RawDetection, Severity, new_id


class StubDetector:
    """Deterministic stand-in for a real object detector. Pure w.r.t. its inputs."""

    def detect(
        self, media: bytes, lat: float, lng: float, captured_at: str, report_id: str
    ) -> list[RawDetection]:
        """Return 0–2 detections derived from a hash of `media`. Deterministic."""
        h = hashlib.sha256(media).digest()

        # Number of detections: 0, 1, or 2 (bias toward 1)
        count = 0 if h[0] % 6 == 0 else 2 if h[0] % 3 == 0 else 1

        detections = []
        for i in range(count):
            seed = h[i * 4 : i * 4 + 4]

            # Class: pothole or garbage
            cls = IssueClass.POTHOLE if seed[0] % 2 == 0 else IssueClass.GARBAGE

            # Confidence: ~0.4–0.98
            confidence = 0.4 + (seed[1] / 255.0) * 0.58

            # Severity
            sev_val = seed[2] % 3
            severity = [Severity.LOW, Severity.MEDIUM, Severity.HIGH][sev_val]

            # Bbox: normalized x, y, w, h in 0..1
            bbox = (
                seed[0] / 255.0 * 0.8,  # x
                seed[1] / 255.0 * 0.8,  # y
                0.1 + seed[2] / 255.0 * 0.15,  # w
                0.1 + seed[3] / 255.0 * 0.15,  # h
            )

            # Geotag: jitter < ~5m (approx 0.00005 deg at equator)
            lat_jitter = ((h[10 + i] / 255.0) - 0.5) * 0.0001
            lng_jitter = ((h[11 + i] / 255.0) - 0.5) * 0.0001

            detections.append(
                RawDetection(
                    id=new_id("det"),
                    report_id=report_id,
                    cls=cls,
                    confidence=confidence,
                    lat=lat + lat_jitter,
                    lng=lng + lng_jitter,
                    captured_at=captured_at,
                    bbox=bbox,
                    severity=severity,
                )
            )

        return detections


def get_detector():
    """Factory that returns the configured detector (stub by default, VLM opt-in via env)."""
    detector_type = os.getenv("TRASHTAG_DETECTOR", "stub")
    if detector_type == "vlm":
        from trashtag.pipeline.vlm import VLMDetector

        return VLMDetector.from_env()
    return StubDetector()
