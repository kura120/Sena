# src/llm/prompts/reasoning_prompts.py
"""
Reasoning Model Prompts

Prompts used by the REASONING model (deepseek-r1 style) to produce
chain-of-thought analysis before the FAST model generates the final reply.

Flow:
  User input + memories + personality + extension results
      ↓
  REASONING model — emits <think>...</think> + structured brief
      ↓
  FAST model — uses brief to form articulate final response
"""

REASONING_PROMPT = """\
You are Sena's reasoning engine. Your job is to think carefully through \
the user's request, drawing on everything you know about them, before \
handing a concise brief to the response model.

--- CONTEXT ---
Relevant memories:
{memories}

User personality profile:
{personality}

Extension results (if any):
{extensions}
--- END CONTEXT ---

User message: {user_message}

Think step by step inside <think> tags. Consider:
- What is the user actually asking or needing?
- Which memories or personality traits are most relevant?
- Are there any implicit goals, preferences, or constraints?
- What tone and approach would work best for this person?

After your thinking, write a concise brief (2-3 sentences **outside** the \
<think> block). The brief must state:
1. What the user needs
2. Any key context from memory or personality worth surfacing in the reply
3. The recommended tone/approach for the response model

Do NOT write the final reply — only the thinking and the brief.
"""


def build_reasoning_prompt(
    user_message: str,
    memories: str = "",
    personality: str = "",
    extensions: str = "",
) -> str:
    """
    Build the full reasoning prompt for a given turn.

    Args:
        user_message: The raw user input.
        memories:     Relevant long-term memories, pre-formatted as a string.
                      Pass an empty string (or omit) when none are available.
        personality:  The personality block string from PersonalityManager.
                      Pass an empty string when not yet built.
        extensions:   Extension output string, e.g. "- web_search: <result>".
                      Pass an empty string when no extensions ran.

    Returns:
        Fully formatted prompt string ready to send to the reasoning model.
    """
    return REASONING_PROMPT.format(
        user_message=user_message,
        memories=memories.strip() if memories else "None",
        personality=personality.strip() if personality else "None",
        extensions=extensions.strip() if extensions else "None",
    )


def parse_reasoning_response(raw: str) -> tuple[str, str]:
    """
    Parse the raw output from the reasoning model into its two parts.

    The model is expected to produce:
        <think>
        ... chain-of-thought ...
        </think>
        ... brief (2-3 sentences) ...

    Args:
        raw: The complete text returned by the reasoning model.

    Returns:
        (think_content, brief) — both stripped.
        If no <think> block is found, think_content is empty and brief is the
        entire raw output.
    """
    import re

    think_match = re.search(r"<think>(.*?)</think>", raw, re.DOTALL | re.IGNORECASE)
    if think_match:
        think_content = think_match.group(1).strip()
        # Everything after the closing </think> tag is the brief
        after_think = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL | re.IGNORECASE).strip()
        brief = after_think
    else:
        think_content = ""
        brief = raw.strip()

    return think_content, brief
