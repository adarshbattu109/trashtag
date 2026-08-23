"""Perceptual-hash frame gate: near-identical frames skip the detector, distinct scenes pass.

Uses deterministic Pillow-generated horizontal gradients — dHash is exact on a monotonic
gradient (increasing → all-0 hash, decreasing → all-1 hash), so the thresholds are stable.
"""

import io

from PIL import Image

from trashtag.pipeline.frames import FrameSelector, dedupe_frames, dhash, hamming

SIZE = 64


def _gradient(descending: bool = False) -> bytes:
    im = Image.new("L", (SIZE, SIZE))
    im.putdata(
        [
            (255 - x * 255 // (SIZE - 1)) if descending else (x * 255 // (SIZE - 1))
            for _y in range(SIZE)
            for x in range(SIZE)
        ]
    )
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def _dimmed(frame: bytes) -> bytes:
    """Same content at half brightness — a lighting change, not a scene change."""
    im = Image.open(io.BytesIO(frame)).point(lambda p: p // 2)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


UP = _gradient(False)
DOWN = _gradient(True)
UP_DIM = _dimmed(UP)


def test_dhash_deterministic():
    assert dhash(UP) == dhash(UP)


def test_hamming_self_is_zero():
    assert hamming(dhash(UP), dhash(UP)) == 0


def test_brightness_change_is_not_a_scene_change():
    # dimming preserves left>right comparisons → identical hash → below threshold → skipped
    assert hamming(dhash(UP), dhash(UP_DIM)) < 10


def test_opposite_gradients_are_distinct():
    assert hamming(dhash(UP), dhash(DOWN)) >= 10


def test_selector_skips_similar_keeps_distinct():
    sel = FrameSelector(threshold=10)
    assert sel.keep(UP) is True  # first frame always kept (anchor)
    assert sel.keep(UP) is False  # identical
    assert sel.keep(UP_DIM) is False  # brightness only
    assert sel.keep(DOWN) is True  # real scene change


def test_dedupe_collapses_a_burst():
    # 200 identical frames + one distinct scene = 2 detector calls, not 201
    burst = [UP] * 200 + [DOWN]
    assert len(dedupe_frames(burst)) == 2


def test_dedupe_retriggers_on_scene_change():
    # up (anchor) → up/up_dim skipped → down (new) → down skipped → up (differs from down) kept
    frames = [UP, UP, UP_DIM, DOWN, DOWN, UP]
    assert len(dedupe_frames(frames)) == 3
