"""Tests for VLM detector — fully offline by monkeypatching _chat."""

import os
from unittest.mock import patch

from trashtag.pipeline.detector import StubDetector, get_detector
from trashtag.pipeline.models import IssueClass, Severity
from trashtag.pipeline.vlm import VLMDetector


def test_vlm_detects_pothole_and_garbage():
    """VLM reply with one pothole + one garbage → 2 RawDetections."""
    detector = VLMDetector()

    canned_reply = """{"detections":[
        {"class":"pothole","confidence":0.85,"severity":"high"},
        {"class":"garbage","confidence":0.72,"severity":"medium"}
    ]}"""

    with patch.object(detector, "_chat", return_value=canned_reply):
        detections = detector.detect(
            media=b"fake image",
            lat=42.3601,
            lng=-71.0589,
            captured_at="2026-08-23T12:00:00Z",
            report_id="rpt_test",
        )

    assert len(detections) == 2

    # First detection: pothole
    assert detections[0].cls == IssueClass.POTHOLE
    assert detections[0].confidence == 0.85
    assert detections[0].severity == Severity.HIGH
    assert detections[0].lat == 42.3601
    assert detections[0].lng == -71.0589
    assert detections[0].captured_at == "2026-08-23T12:00:00Z"
    assert detections[0].report_id == "rpt_test"
    assert detections[0].bbox is None

    # Second detection: garbage
    assert detections[1].cls == IssueClass.GARBAGE
    assert detections[1].confidence == 0.72
    assert detections[1].severity == Severity.MEDIUM


def test_vlm_empty_detections():
    """VLM reply with no detections → []."""
    detector = VLMDetector()

    with patch.object(detector, "_chat", return_value='{"detections":[]}'):
        detections = detector.detect(
            media=b"clean street",
            lat=42.0,
            lng=-71.0,
            captured_at="2026-08-23T12:00:00Z",
            report_id="rpt_clean",
        )

    assert detections == []


def test_vlm_malformed_reply():
    """VLM reply with malformed/non-JSON → [] (graceful degradation)."""
    detector = VLMDetector()

    # Non-JSON reply
    with patch.object(detector, "_chat", return_value="This is not JSON"):
        detections = detector.detect(
            media=b"image",
            lat=42.0,
            lng=-71.0,
            captured_at="2026-08-23T12:00:00Z",
            report_id="rpt_bad",
        )
    assert detections == []

    # Malformed JSON
    with patch.object(detector, "_chat", return_value='{"detections": [broken}'):
        detections = detector.detect(
            media=b"image",
            lat=42.0,
            lng=-71.0,
            captured_at="2026-08-23T12:00:00Z",
            report_id="rpt_bad2",
        )
    assert detections == []

    # Empty reply
    with patch.object(detector, "_chat", return_value=""):
        detections = detector.detect(
            media=b"image",
            lat=42.0,
            lng=-71.0,
            captured_at="2026-08-23T12:00:00Z",
            report_id="rpt_bad3",
        )
    assert detections == []


def test_vlm_skips_unknown_class():
    """VLM reply with unknown class is skipped."""
    detector = VLMDetector()

    canned_reply = """{"detections":[
        {"class":"graffiti","confidence":0.9,"severity":"low"},
        {"class":"pothole","confidence":0.8,"severity":"high"}
    ]}"""

    with patch.object(detector, "_chat", return_value=canned_reply):
        detections = detector.detect(
            media=b"image",
            lat=42.0,
            lng=-71.0,
            captured_at="2026-08-23T12:00:00Z",
            report_id="rpt_mixed",
        )

    # Only the pothole should be included
    assert len(detections) == 1
    assert detections[0].cls == IssueClass.POTHOLE


def test_vlm_clamps_confidence():
    """Confidence values outside [0,1] are clamped."""
    detector = VLMDetector()

    canned_reply = """{"detections":[
        {"class":"pothole","confidence":1.5,"severity":"high"},
        {"class":"garbage","confidence":-0.2,"severity":"low"}
    ]}"""

    with patch.object(detector, "_chat", return_value=canned_reply):
        detections = detector.detect(
            media=b"image",
            lat=42.0,
            lng=-71.0,
            captured_at="2026-08-23T12:00:00Z",
            report_id="rpt_clamp",
        )

    assert detections[0].confidence == 1.0  # Clamped to 1.0
    assert detections[1].confidence == 0.0  # Clamped to 0.0


def test_get_detector_default_is_stub():
    """get_detector() returns StubDetector by default."""
    with patch.dict(os.environ, {}, clear=False):
        # Ensure TRASHTAG_DETECTOR is not set
        os.environ.pop("TRASHTAG_DETECTOR", None)
        detector = get_detector()
        assert isinstance(detector, StubDetector)


def test_get_detector_vlm_when_env_set():
    """get_detector() returns VLMDetector when TRASHTAG_DETECTOR=vlm."""
    with patch.dict(os.environ, {"TRASHTAG_DETECTOR": "vlm"}):
        detector = get_detector()
        assert isinstance(detector, VLMDetector)
