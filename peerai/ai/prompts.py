"""One prompt per target kind. Short outputs: this lives in a side panel, not a chat."""
from __future__ import annotations

from ..events import Target, TargetKind

SYSTEM = (
    "You are a quiet heads-up assistant. The user is looking at something on their screen "
    "and you have its text or an image of it. Reply in plain prose, at most 120 words, "
    "no preamble, no headings, no markdown. If there is nothing useful to say, say so in one line."
)

_TEMPLATES: dict[TargetKind, str] = {
    "text": (
        "Summarise the passage in two or three sentences and add one line of useful context "
        "(what it is about, why it matters, or a key term explained).\n\nPassage:\n{text}"
    ),
    "question": (
        "The user is looking at a question. Answer it directly and briefly, then give one sentence "
        "of justification. If it has options, name the correct one.\n\nQuestion:\n{text}"
    ),
    "code": (
        "Explain what this code does in two or three sentences, and point out one thing worth "
        "knowing (a bug, a pitfall, or the key idea).\n\nCode:\n{text}"
    ),
    "ui_element": (
        "The user is looking at a control in the app '{app}' (window: '{title}'). Its label is: "
        "'{text}'. In one or two sentences, say what it most likely does."
    ),
    "image": (
        "Describe what this image shows in two or three sentences. If it contains text, quote the "
        "important part. If it is a chart or diagram, state the main takeaway."
    ),
    "unknown": "Describe what this is in one or two sentences.\n\nContent:\n{text}",
}


def build_prompt(kind: TargetKind, target: Target) -> str:
    template = _TEMPLATES.get(kind, _TEMPLATES["unknown"])
    prompt = template.format(text=target.text, app=target.app_name, title=target.window_title)
    if kind == "image" and target.text.strip():
        prompt += f"\n\nNearby text or caption: {target.text[:300]}"
    return prompt
