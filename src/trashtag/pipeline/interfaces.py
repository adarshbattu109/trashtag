"""Pluggable seams for the pipeline. Only the genuinely two-implementation boundaries get a
Protocol; everything else is a concrete class (ponytail: no interface for a single impl).

`Detector` is the real one: a deterministic stub ships now, a fine-tuned YOLO/ONNX detector
swaps in behind the same signature later (architecture §2.2 / §4).
"""

from typing import Protocol

from trashtag.pipeline.models import RawDetection


class Detector(Protocol):
    """Turns one media file into zero or more detections.

    Implementations must be pure w.r.t. their inputs (same bytes + coords → same detections),
    so the pipeline is testable without a GPU. The confidence gate is applied by the caller
    (process stage), not the detector — a detector reports everything it sees.
    """

    def detect(
        self, media: bytes, lat: float, lng: float, captured_at: str, report_id: str
    ) -> list[RawDetection]:
        """Return detections found in `media`, each geotagged (default to the report's
        lat/lng; a real detector may refine per-detection). `report_id` links provenance."""
        ...
