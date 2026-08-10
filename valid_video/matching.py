"""Deterministic filename-stem heuristic for grouping same-creative videos.

Filenames are expected to follow the convention `{stem}_{ratio}.{ext}`,
e.g. `campaign123_9-16.mp4`. This module strips the ratio suffix (only
when it matches one of the canonical ratios) and extension to recover
the shared "stem" that identifies the underlying creative, then groups
filenames by that stem.

This is a stand-in for real perceptual video matching -- see module
docstring in pipeline.py for context on that tradeoff.
"""

import os
import re
from collections import OrderedDict

# Canonical ratio suffixes as they appear in filenames (hyphenated).
_KNOWN_RATIO_SUFFIXES = ("9-16", "1-1", "4-5", "16-9")

# Matches a trailing ratio suffix, optionally preceded by an "AS" marker
# (agency naming convention, e.g. "..._4685__AS_9-16.mp4"). The "AS" marker
# and any underscores immediately around it are stripped along with the
# ratio itself, so both of these produce the same clean stem:
#   campaign123_9-16.mp4                 -> campaign123
#   ..._4685__AS_9-16.mp4                -> ..._4685
_RATIO_SUFFIX_PATTERN = re.compile(
    r"(?:_+AS)?_(" + "|".join(re.escape(r) for r in _KNOWN_RATIO_SUFFIXES) + r")$",
    re.IGNORECASE,
)


def extract_stem(filename: str) -> str:
    """Return the creative "stem" for a filename.

    Strips directory components, the file extension, and -- only if
    present -- a trailing `_{known_ratio}` suffix. Unrecognized suffixes
    are left in place, since stripping them could incorrectly merge
    unrelated videos.
    """
    basename = os.path.basename(filename)
    name_without_ext, _ext = os.path.splitext(basename)

    match = _RATIO_SUFFIX_PATTERN.search(name_without_ext)
    if match:
        return name_without_ext[: match.start()]

    return name_without_ext


def group_by_stem(filenames: list[str]) -> dict[str, list[str]]:
    """Group filenames by their extracted stem, preserving input order."""
    groups: "OrderedDict[str, list[str]]" = OrderedDict()
    for filename in filenames:
        stem = extract_stem(filename)
        groups.setdefault(stem, []).append(filename)
    return dict(groups)
