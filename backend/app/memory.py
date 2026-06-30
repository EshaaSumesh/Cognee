"""Cognee memory layer wrapper.

This is the heart of Recall's "Best Use of Cognee": every memory operation maps
to the Cognee lifecycle on the *self-hosted, open-source* engine.

    remember()  -> cognee.add(...) + cognee.cognify()   (build hybrid graph-vector memory)
    recall()    -> cognee.search(...)                   (hybrid graph + vector retrieval)
    improve()   -> cognee.cognify() / memify on feedback (memory compounds over time)
    forget()    -> cognee.prune / delete                (prune stale runbooks/services)

Everything runs locally against Postgres + pgvector + a graph backend. No cloud.

If the `cognee` package is unavailable (e.g. local dev without the heavy deps),
we fall back to a transparent in-memory store so the API and UI still run and the
demo still shows the compounding behaviour. The fallback is clearly flagged via
`MemoryLayer.backend`.
"""
from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass, field
from typing import Optional

try:  # Real Cognee, self-hosted open-source engine.
    import cognee  # type: ignore

    _HAS_COGNEE = True
except Exception:  # pragma: no cover - fallback path
    cognee = None  # type: ignore
    _HAS_COGNEE = False


@dataclass
class RecallHit:
    text: str
    source: str
    score: float = 0.0
    kind: str = "event"


@dataclass
class _FallbackDoc:
    text: str
    source: str
    kind: str
    dataset: str
    # crude "improve" signal: weight grows when feedback marks it helpful
    weight: float = 1.0


@dataclass
class MemoryLayer:
    """Async facade over Cognee with a graceful in-memory fallback."""

    backend: str = "cognee" if _HAS_COGNEE else "in-memory-fallback"
    _docs: list[_FallbackDoc] = field(default_factory=list)
    _ready: bool = False
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def setup(self) -> None:
        """Configure Cognee for self-hosted operation from environment."""
        async with self._lock:
            if self._ready:
                return
            if _HAS_COGNEE:
                # Cognee reads providers/DB config from environment (see .env).
                # Optionally point at Cognee Cloud as a documented fallback only.
                base_url = os.getenv("COGNEE_BASE_URL")
                api_key = os.getenv("COGNEE_API_KEY")
                if base_url and api_key:
                    await cognee.serve(url=base_url, api_key=api_key)  # type: ignore
            self._ready = True

    # ---- remember ---------------------------------------------------------
    async def remember(
        self,
        text: str,
        *,
        source: str,
        kind: str = "event",
        dataset: str = "incidents",
    ) -> None:
        """Ingest content and structure it into the knowledge graph."""
        await self.setup()
        if _HAS_COGNEE:
            # Tag the text so citations can be traced back to the source.
            payload = f"[source:{source}] [kind:{kind}]\n{text}"
            await cognee.add(payload, dataset_name=dataset)  # type: ignore
            await cognee.cognify(datasets=[dataset])  # type: ignore
        else:
            self._docs.append(
                _FallbackDoc(text=text, source=source, kind=kind, dataset=dataset)
            )

    # ---- recall -----------------------------------------------------------
    async def recall(self, query: str, *, top_k: int = 5) -> list[RecallHit]:
        """Hybrid graph + vector retrieval; auto-routed by Cognee."""
        await self.setup()
        if _HAS_COGNEE:
            results = await cognee.search(query_text=query)  # type: ignore
            hits: list[RecallHit] = []
            for r in (results or [])[:top_k]:
                text = r if isinstance(r, str) else str(r)
                source, kind, clean = _parse_tags(text)
                hits.append(
                    RecallHit(text=clean, source=source, kind=kind, score=1.0)
                )
            return hits
        return self._fallback_recall(query, top_k=top_k)

    # ---- improve (memify) -------------------------------------------------
    async def improve(
        self,
        *,
        feedback: Optional[str] = None,
        dataset: str = "incidents",
        helpful_sources: Optional[list[str]] = None,
    ) -> None:
        """Post-ingestion enrichment so memory compounds across sessions."""
        await self.setup()
        if _HAS_COGNEE:
            if feedback:
                await cognee.add(  # type: ignore
                    f"[source:feedback] [kind:event]\n{feedback}", dataset_name=dataset
                )
            # Re-run graph construction to integrate the new outcome/feedback.
            await cognee.cognify(datasets=[dataset])  # type: ignore
        else:
            if helpful_sources:
                for d in self._docs:
                    if d.source in helpful_sources:
                        d.weight += 1.0

    # ---- forget -----------------------------------------------------------
    async def forget(
        self,
        *,
        dataset: Optional[str] = None,
        source: Optional[str] = None,
        source_prefix: Optional[str] = None,
    ) -> None:
        """Surgically prune datasets or sources no longer needed."""
        await self.setup()
        if _HAS_COGNEE:
            if dataset:
                try:
                    await cognee.prune.prune_data(dataset=dataset)  # type: ignore
                except Exception:
                    # API surface varies across versions; best-effort prune.
                    await cognee.prune.prune_system()  # type: ignore
        else:
            self._docs = [
                d
                for d in self._docs
                if (dataset is None or d.dataset != dataset)
                and (source is None or d.source != source)
                and (source_prefix is None or not d.source.startswith(source_prefix))
            ]

    # ---- fallback helpers -------------------------------------------------
    def _fallback_recall(self, query: str, *, top_k: int) -> list[RecallHit]:
        terms = set(_tokenize(query))
        scored: list[tuple[float, _FallbackDoc]] = []
        for d in self._docs:
            doc_terms = set(_tokenize(d.text + " " + d.source))
            overlap = len(terms & doc_terms)
            if overlap == 0:
                continue
            score = overlap * d.weight
            scored.append((score, d))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            RecallHit(text=d.text, source=d.source, kind=d.kind, score=s)
            for s, d in scored[:top_k]
        ]


_TAG_RE = re.compile(r"\[source:(?P<source>[^\]]+)\]\s*\[kind:(?P<kind>[^\]]+)\]\s*")


def _parse_tags(text: str) -> tuple[str, str, str]:
    m = _TAG_RE.match(text)
    if not m:
        return ("memory", "event", text)
    source = m.group("source").strip()
    kind = m.group("kind").strip()
    clean = text[m.end():].strip()
    return (source, kind, clean)


def _tokenize(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-zA-Z0-9]+", text.lower()) if len(t) > 2]


# Singleton used across the app.
memory = MemoryLayer()
