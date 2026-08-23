"""VLMDetector tolerates markdown-fenced / prose-wrapped JSON (real VLMs do this despite the
'JSON only' instruction). Offline — _chat is monkeypatched, no network."""

from trashtag.pipeline.vlm import VLMDetector, _extract_json


def test_extract_json_strips_markdown_fence():
    fenced = '```json\n{"detections": [{"class": "pothole"}]}\n```'
    assert _extract_json(fenced) == '{"detections": [{"class": "pothole"}]}'


def test_extract_json_strips_leading_prose():
    prose = 'Here is what I found:\n{"detections": []} hope that helps'
    assert _extract_json(prose) == '{"detections": []}'


def test_detect_parses_fenced_reply(monkeypatch):
    det = VLMDetector()
    monkeypatch.setattr(
        det,
        "_chat",
        lambda *a, **k: (
            '```json\n{"detections":[{"class":"pothole","confidence":0.9,"severity":"high"}]}\n```'
        ),
    )
    out = det.detect(b"img", 18.52, 73.85, "2026-08-23T00:00:00", "rpt_x")
    assert len(out) == 1
    assert str(out[0].cls) == "pothole"
    assert out[0].confidence == 0.9


def test_detect_handles_unparseable_reply(monkeypatch):
    det = VLMDetector()
    monkeypatch.setattr(det, "_chat", lambda *a, **k: "sorry, I cannot help with that")
    assert det.detect(b"img", 18.52, 73.85, "2026-08-23T00:00:00", "rpt_x") == []
