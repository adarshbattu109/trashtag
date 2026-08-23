"""Perceptual-hash frame gate — the anti-spam layer for video/burst capture (§2.2, §3.1).

Running a detector (VLM or YOLO) on every video frame is ruinous: a phone mounted at a red
light stares at the same pothole for hundreds of near-identical frames. This gate keeps only
frames that are *visually different* from the last one kept, so 200 frames of one scene cost
ONE detector call, not 200. It sits BEFORE detection; the §2.3 geospatial dedup is the second
layer that merges detections across separate reports afterwards.

Difference-hash (dHash) + Hamming distance: cheap, and invariant to brightness/scale changes
(monotonic pixel changes preserve the left>right comparisons), so a lighting flicker between
frames does not count as a new scene — only real content change does.
"""

import io

from PIL import Image

from trashtag.helper.config import FRAME_THRESHOLD


def dhash(image_bytes: bytes, hash_size: int = 8) -> int:
    """64-bit difference hash of an image (default 8 → 64 bits).

    Grayscale, resize to (hash_size+1, hash_size), then for each row emit a bit per adjacent
    pixel pair (1 if left brighter than right). Relative comparisons make it robust to overall
    brightness/contrast shifts between video frames.
    """
    img = (
        Image.open(io.BytesIO(image_bytes))
        .convert("L")
        .resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    )
    px = list(img.getdata())
    row_stride = hash_size + 1
    bits = 0
    for row in range(hash_size):
        base = row * row_stride
        for col in range(hash_size):
            bits = (bits << 1) | int(px[base + col] > px[base + col + 1])
    return bits


def hamming(a: int, b: int) -> int:
    """Number of differing bits between two hashes."""
    return (a ^ b).bit_count()


class FrameSelector:
    """Stateful gate: `.keep(frame)` is True only when the frame differs from the last KEPT
    frame by at least `threshold` bits. Compares against the last kept frame (an anchor), so
    slow drift eventually crosses the threshold and starts a new keyframe.
    """

    def __init__(self, threshold: int = FRAME_THRESHOLD, hash_size: int = 8):
        self.threshold = threshold
        self.hash_size = hash_size
        self._last: int | None = None

    def keep(self, image_bytes: bytes) -> bool:
        """True if this frame is a new distinct scene (and should be sent to the detector)."""
        h = dhash(image_bytes, self.hash_size)
        if self._last is None or hamming(h, self._last) >= self.threshold:
            self._last = h
            return True
        return False


def dedupe_frames(
    frames, threshold: int = FRAME_THRESHOLD, hash_size: int = 8
) -> list[bytes]:
    """Filter a sequence of frames down to the visually-distinct ones the detector must see.

    Args:
        frames: an iterable of image byte-strings (already sampled, e.g. ~1 fps, per §3.1).
        threshold: Hamming distance below which two frames are "the same scene".

    Returns:
        The kept frames, in order — typically far fewer than the input for real footage.
    """
    selector = FrameSelector(threshold, hash_size)
    return [f for f in frames if selector.keep(f)]
