"""The program spec's redaction map, applied before any evidence is written.

Spec (2026-07-03 phase5-emulation-program, rev 2): the Atlassian base URL becomes
``https://ATLASSIAN.example``; the project key becomes ``PROJ``; the space key becomes
``SPACE``; issue/page ids become ``{id}``. The GitHub/GitLab lab repo slugs are committed AS-IS
(they are our disposable lab assets, not instance data), so they are never redacted. Instance
data is replaced before anything is committed so the corpus stays regenerable and safe.
"""

from __future__ import annotations

from dataclasses import dataclass

ATLASSIAN_BASE_TOKEN = "https://ATLASSIAN.example"
PROJECT_KEY_TOKEN = "PROJ"
SPACE_KEY_TOKEN = "SPACE"
ID_TOKEN = "{id}"


@dataclass(frozen=True)
class RedactionMap:
    """The instance-specific values to strip from evidence. All fields are optional: an offline
    GitHub row supplies none (there is nothing Atlassian to redact), a live Jira/Confluence row
    supplies the real base URL and keys. ``ids`` are the concrete issue/page ids to mask."""

    atlassian_base: str | None = None
    project_key: str | None = None
    space_key: str | None = None
    ids: tuple[str, ...] = ()

    def apply(self, text: str) -> str:
        """Return ``text`` with every configured instance value replaced by its stable token.

        Order is load-bearing: the base URL first (an id can be a substring of a URL), then the
        keys, then the ids from longest to shortest so a shorter id never masks a longer one."""

        redacted = text
        if self.atlassian_base:
            redacted = redacted.replace(self.atlassian_base.rstrip("/"), ATLASSIAN_BASE_TOKEN)
        if self.project_key:
            redacted = redacted.replace(self.project_key, PROJECT_KEY_TOKEN)
        if self.space_key:
            redacted = redacted.replace(self.space_key, SPACE_KEY_TOKEN)
        for value in sorted(self.ids, key=len, reverse=True):
            if value:
                redacted = redacted.replace(value, ID_TOKEN)
        return redacted


NULL_REDACTION = RedactionMap()
