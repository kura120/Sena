# src/llm/prompts/intent_prompts.py
"""
Intent Classification and Memory Extraction Prompts
"""

INTENT_CLASSIFICATION_PROMPT = """Analyze the following user message and classify its intent.

User Message: {user_input}

Classify into exactly ONE of these intents:
- greeting: Hello, hi, hey, good morning, etc.
- farewell: Goodbye, bye, see you later, etc.
- general_conversation: Casual chat, small talk
- question: Asking for information or explanation
- complex_query: Deep analysis, multi-step reasoning, complex problems
- code_request: Write code, create program, implement feature
- code_explanation: Explain code, debug, code review
- system_command: Open app, run program, system operation
- web_search: Search the web, find online information
- file_operation: Read/write/manage files
- memory_recall: Remember something from past conversation
- creative_writing: Write story, poem, creative content
- analysis: Analyze data, compare options, evaluate
- math: Mathematical calculations or problems
- translation: Translate between languages
- summarization: Summarize text or content
- unknown: Cannot determine intent

Respond with ONLY the intent name in lowercase, nothing else."""


MEMORY_EXTRACTION_PROMPT = """Analyze the following conversation and extract important information that should be remembered long-term.

Conversation:
{conversation}

Extract the following types of information if present:
1. Facts about the user (name, preferences, occupation, etc.)
2. Important events or dates mentioned
3. User's opinions and preferences
4. Recurring topics of interest
5. Technical details or project information
6. Relationships and connections mentioned

For each piece of information, provide:
- The information itself
- Category (user_fact, event, preference, interest, technical, relationship)
- Importance score (1-10)

Format as JSON array:
[
  {{"content": "...", "category": "...", "importance": N}},
  ...
]

If no important information to extract, return empty array: []

Important information to remember:"""


MEMORY_RELEVANCE_PROMPT = """Given the user's current message and the retrieved memory, determine if the memory is relevant.

Current message: {user_input}

Retrieved memory: {memory_content}

Is this memory relevant to the current conversation?
Respond with only "yes" or "no"."""


CONVERSATION_SUMMARY_PROMPT = """Summarize the following conversation in 2-3 sentences, capturing the main topic and key points.

Conversation:
{conversation}

Summary:"""


SESSION_TITLE_PROMPT = """Generate a very short session title (3-6 words maximum) that captures the main topic of this conversation opener.

User message: {message}

Rules:
- Maximum 6 words
- No punctuation at the end
- Title case
- Be specific, not generic (avoid "Chat Session", "New Conversation")
- Focus on the actual topic/task

Respond with ONLY the title, nothing else."""


MEMORY_STORE_DETECTION_PROMPT = """Analyze the following user message and determine if the user is explicitly asking to store or remember a specific piece of information for future reference.

User message: {message}

Examples of STORE requests:
- "remember this number: 6"
- "remember that my name is Alex"
- "please remember I prefer dark mode"
- "store this: my API key is abc123"
- "keep in mind that I work at Acme Corp"
- "don't forget my birthday is March 15"

Examples of NON-STORE requests:
- "do you remember what we talked about?"  (recall, not store)
- "what did I tell you earlier?"  (recall)
- "remember when we discussed Python?"  (rhetorical/recall)
- "I remember now"  (user statement, not a store request)

If this IS a store request, extract EXACTLY what should be stored (the actual information content, not the instruction to remember it).

Respond in this exact JSON format:
{{"is_store": true/false, "content": "the exact information to store or null"}}

Respond with ONLY the JSON, nothing else."""


EXTENSION_GENERATION_PROMPT = """Create a Python extension for Sena based on the following description:

Description: {description}

Requirements:
1. Must include VERSION constant (string, e.g., "1.0.0")
2. Must include METADATA dictionary with:
   - name: Extension name (lowercase, underscores)
   - description: What it does
   - author: "AI Generated"
   - parameters: Dict of parameter names to descriptions
   - requires: List of required extensions (can be empty)
3. Must include async execute(user_input: str, context: dict, **kwargs) function
4. Optionally include validate(user_input: str, **kwargs) function
5. Use only allowed imports: os, sys, json, re, datetime, pathlib, typing, collections, itertools, functools, math, random, string, urllib, base64, httpx
6. Handle errors gracefully
7. Return string result from execute()

Generate clean, well-documented Python code:

```python
"""
