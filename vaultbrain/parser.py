"""Vault Markdown parser extracting frontmatter, wikilinks, tags, and headings."""

from __future__ import annotations

import os
import re
import yaml
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
WIKILINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")
HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
INLINE_TAG_PATTERN = re.compile(r"(?:^|\s)#([a-zA-Z0-9_\-\/]+)")

EXCLUDED_DIRS = {".git", ".obsidian", ".trash", ".smart-env", "node_modules", ".venv", "venv"}


@dataclass
class Note:
    path: str
    rel_path: str
    title: str
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    headings: List[str] = field(default_factory=list)
    wikilinks: List[Dict[str, Optional[str]]] = field(default_factory=list)
    raw_content: str = ""


def parse_markdown_file(file_path: str, vault_root: str) -> Note:
    """Parse a single markdown file into a structured Note object."""
    rel_path = os.path.relpath(file_path, vault_root)
    file_stem = os.path.splitext(os.path.basename(file_path))[0]

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    frontmatter: Dict[str, Any] = {}
    body = content

    # 1. Parse YAML frontmatter
    fm_match = FRONTMATTER_PATTERN.match(content)
    if fm_match:
        yaml_text = fm_match.group(1)
        body = content[fm_match.end():]
        try:
            loaded = yaml.safe_load(yaml_text)
            if isinstance(loaded, dict):
                # Normalize dates/times to string for consistent serialization
                frontmatter = {
                    k: (v.isoformat() if hasattr(v, "isoformat") else v)
                    for k, v in loaded.items()
                }
        except yaml.YAMLError:
            frontmatter = {}

    # 2. Extract tags (from frontmatter and inline)
    tags_set = set()
    # Frontmatter tags can be list or comma-separated string
    fm_tags = frontmatter.get("tags", [])
    if isinstance(fm_tags, list):
        for t in fm_tags:
            if t:
                tags_set.add(str(t).lstrip("#").strip())
    elif isinstance(fm_tags, str):
        for t in fm_tags.split(","):
            if t.strip():
                tags_set.add(t.strip().lstrip("#"))

    # Frontmatter tag singular
    fm_tag = frontmatter.get("tag")
    if isinstance(fm_tag, str):
        tags_set.add(fm_tag.strip().lstrip("#"))

    # Inline tags in body
    for it in INLINE_TAG_PATTERN.findall(body):
        # Ignore purely numeric tags or hex
        if not it.isdigit() and len(it) > 1:
            tags_set.add(it)

    # 3. Extract aliases
    aliases_set = set()
    fm_aliases = frontmatter.get("aliases", [])
    if isinstance(fm_aliases, list):
        for a in fm_aliases:
            if a:
                aliases_set.add(str(a).strip())
    elif isinstance(fm_aliases, str):
        aliases_set.add(fm_aliases.strip())

    # 4. Extract headings
    headings = [h.strip() for h in HEADING_PATTERN.findall(body)]

    # 5. Extract wikilinks: [[Target#Section|Alias]]
    wikilinks: List[Dict[str, Optional[str]]] = []
    seen_links = set()

    for raw_link in WIKILINK_PATTERN.findall(content):
        raw_link = raw_link.strip()
        if not raw_link:
            continue

        target_part, has_alias, alias_part = raw_link.partition("|")
        alias = alias_part.strip() if has_alias else None

        target_clean, has_sec, section_part = target_part.partition("#")
        section = section_part.strip() if has_sec else None

        # Clean and sanitize target name
        target = target_clean.strip()
        if target.endswith(".md"):
            target = target[:-3].strip()

        if not target and section:
            # Anchor link to self
            target = file_stem

        # Sanitize path traversal in target
        target = target.replace("\\", "/").strip()
        while "../" in target:
            target = target.replace("../", "")
        target = target.lstrip("/")

        # Normalize directory path to note stem if it contains subdirectories
        if "/" in target:
            target = os.path.basename(target).strip()

        # If target is still empty, skip this malformed link
        if not target:
            continue

        link_key = (target, section, alias)
        if link_key not in seen_links:
            seen_links.add(link_key)
            wikilinks.append({
                "target": target,
                "alias": alias,
                "section": section,
            })

    return Note(
        path=file_path,
        rel_path=rel_path,
        title=file_stem,
        frontmatter=frontmatter,
        tags=sorted(tags_set),
        aliases=sorted(aliases_set),
        headings=headings,
        wikilinks=wikilinks,
        raw_content=content,
    )


def parse_vault(vault_root: str) -> List[Note]:
    """Scan vault directory and parse all markdown files."""
    notes: List[Note] = []

    for root, dirs, files in os.walk(vault_root):
        # Prune excluded directories
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS and not d.startswith(".")]

        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                notes.append(parse_markdown_file(file_path, vault_root))

    return notes
