# src/llm/prompts/personality_prompts.py
"""
Personality Prompts for Sena

Prompts used by the PersonalityManager to:
1. Infer personality fragments from conversations
2. Compress many fragments into a concise summary block for the system prompt
"""

# ──────────────────────────────────────────────────────────────────────────────
# Inference Prompt
# ──────────────────────────────────────────────────────────────────────────────

PERSONALITY_INFERENCE_PROMPT = """You are analyzing a conversation between a user and Sena (an AI assistant).
Your job is to extract NEW, SPECIFIC facts about the USER's preferences, personality, habits, or important personal details.

These fragments will be used to make Sena more personalized in future conversations.

## Rules
- Extract ONLY facts that are clearly stated or strongly implied by the user (not Sena).
- Do NOT extract vague or obvious facts (e.g. "user likes talking to AI" is too generic).
- Do NOT duplicate facts that already exist in the known fragments list below.
- Each fragment must be a single, self-contained, specific fact.
- Assign a confidence score (0.0 to 1.0) reflecting how certain you are this is a genuine personal fact.
  - 1.0 = user explicitly stated it ("I hate spicy food")
  - 0.7-0.9 = strongly implied ("I always skip breakfast" → user skips breakfast regularly)
  - 0.5-0.69 = inferred from context (borderline, less certain)
  - Below 0.5 = do not include
- Assign a category from: preference, trait, habit, fact, goal, dislike, relationship, work, health, hobby

## Already Known Fragments (do not duplicate)
{known_fragments}

## Conversation to Analyze
{conversation}

## Output Format
Respond ONLY with a valid JSON array. Each element must have these exact keys:
- "content": string — the personality fact (concise, first-person from Sena's perspective, e.g. "The user prefers dark mode interfaces")
- "confidence": float — 0.0 to 1.0
- "category": string — one of the categories listed above

If no new fragments are found, respond with an empty array: []

Example output:
[
  {{"content": "The user prefers dark mode interfaces", "confidence": 0.95, "category": "preference"}},
  {{"content": "The user works as a software engineer", "confidence": 0.88, "category": "fact"}},
  {{"content": "The user dislikes meetings that could have been emails", "confidence": 0.82, "category": "dislike"}}
]

JSON array:"""


# ──────────────────────────────────────────────────────────────────────────────
# Compression Prompt
# ──────────────────────────────────────────────────────────────────────────────

PERSONALITY_COMPRESSION_PROMPT = """You are compressing a list of personality facts about a user into a compact,
coherent summary that will be injected into an AI assistant's system prompt.

## Goal
Produce a concise but information-dense summary that:
- Preserves all important, specific facts
- Groups related facts together
- Uses clear, direct language
- Fits within approximately {target_tokens} tokens
- Is written from Sena's perspective (e.g. "The user prefers...", "The user works as...")

## Fragments to Compress
{fragments}

## Output Format
Respond ONLY with the compressed summary text. No preamble, no JSON, no explanation.
Start directly with the summary content.

Compressed summary:"""


# ──────────────────────────────────────────────────────────────────────────────
# System Prompt Block Template
# ──────────────────────────────────────────────────────────────────────────────

PERSONALITY_BLOCK_TEMPLATE = """## What You Know About This User

The following are established facts about the user, learned from previous conversations.
Treat these as ground truth. Reference them naturally when relevant — do not re-ask for
information you already know.

{personality_content}
"""

PERSONALITY_BLOCK_EMPTY = """## What You Know About This User

You are still learning about this user. No personal preferences or facts have been confirmed yet.
Pay attention to what they share and adapt your responses accordingly.
"""


# ──────────────────────────────────────────────────────────────────────────────
# Helper builders
# ──────────────────────────────────────────────────────────────────────────────


def build_inference_prompt(conversation: str, known_fragments: list[str]) -> str:
    """
    Build the fully-rendered personality inference prompt.

    Args:
        conversation: Raw conversation text (user + assistant turns).
        known_fragments: List of already-approved fragment content strings,
                         used to avoid duplicates.

    Returns:
        Rendered prompt string ready to send to the LLM.
    """
    if known_fragments:
        known_block = "\n".join(f"- {f}" for f in known_fragments)
    else:
        known_block = "(none yet)"

    return PERSONALITY_INFERENCE_PROMPT.format(
        known_fragments=known_block,
        conversation=conversation,
    )


def build_compression_prompt(fragments: list[str], target_tokens: int = 400) -> str:
    """
    Build the fully-rendered personality compression prompt.

    Args:
        fragments: List of approved fragment content strings to compress.
        target_tokens: Approximate token budget for the output summary.

    Returns:
        Rendered prompt string ready to send to the LLM.
    """
    fragments_block = "\n".join(f"- {f}" for f in fragments)
    return PERSONALITY_COMPRESSION_PROMPT.format(
        fragments=fragments_block,
        target_tokens=target_tokens,
    )


def build_personality_block(personality_content: str | None) -> str:
    """
    Wrap personality content in the system prompt block template.

    Args:
        personality_content: The compressed/raw personality text to inject,
                             or None/empty if no personality data exists yet.

    Returns:
        Formatted personality block string for inclusion in the system prompt.
    """
    if not personality_content or not personality_content.strip():
        return PERSONALITY_BLOCK_EMPTY

    return PERSONALITY_BLOCK_TEMPLATE.format(personality_content=personality_content.strip())
