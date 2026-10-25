
"""
Clarification Agent for GeneScope AI.

Checks research intent and the current indexed collection
before research begins.

This is a rule-based first version, not an LLM classifier.
"""

import re

from src.graph.state import ResearchState


# Match whole requests with no research subject. A topic-bearing question
# such as "What should I investigate about APOE?" should still proceed.
VAGUE_REQUEST = re.compile(
    r"(?:please )?(?:"
    r"what (?:should|could|can) (?:i|we) "
    r"(?:do|investigate|research|explore|study)(?: next)?"
    r"|what (?:is|are) (?:the |our |my )?next steps?"
    r"|what next"
    r"|(?:tell|show) (?:me|us) what to (?:investigate|research|explore|study|do)(?: next)?"
    r")(?: please)?"
)

COLLECTION_TERMS = re.compile(
    r"\b(?:apoe|apolipoprotein\s+e|alzheimer\w*|dementia|"
    r"amyloid|tau|epsilon\s*[234]|[εϵ]\s*[234]|e[234])\b"
)

# Conservative negative rules, not a whitelist of permitted wording.
# Unknown terminology proceeds to the existing evidence checks. Extend these
# markers as new clearly unrelated topics are encountered in this prototype.
UNRELATED_TOPICS = re.compile(
    r"\b(?:brca[12]|tp53|cftr|hbb|htt|smn[12]|fmr1|dmd|hfe|"
    r"(?:breast|ovarian|lung|prostate|colorectal) cancer|"
    r"cystic fibrosis|sickle cell|huntington\w*|hemophilia)\b"
)


def clarification_agent(state: ResearchState) -> dict:
    """Request missing intent or stop a clearly unrelated research topic."""

    question = state["question"].casefold()
    normalized_question = " ".join(re.findall(r"\w+", question))
    defaults = {
        "needs_clarification": False,
        "clarification_question": "",
        "out_of_scope": False,
        "scope_message": "",
    }

    if not normalized_question:
        return {
            **defaults,
            "needs_clarification": True,
            "clarification_question": (
                "What gene or scientific question would you "
                "like to investigate?"
            ),
            "agent_log": state.get("agent_log", []) + [
                "Clarification Agent: empty research question."
            ],
        }

    if VAGUE_REQUEST.fullmatch(normalized_question):
        return {
            **defaults,
            "needs_clarification": True,
            "clarification_question": (
                "Would you like to investigate genetic risk, "
                "biological mechanisms, or therapeutic approaches? "
                "Please specify your research objective."
            ),
            "agent_log": state.get("agent_log", []) + [
                "Clarification Agent: research objective is ambiguous."
            ],
        }

    unrelated_topic = UNRELATED_TOPICS.search(question)
    if unrelated_topic and not COLLECTION_TERMS.search(question):
        topic = unrelated_topic.group()
        if re.fullmatch(r"[a-z]+\d*", topic):
            topic = topic.upper()
        return {
            **defaults,
            "out_of_scope": True,
            "scope_message": (
                "GeneScope AI currently contains research on APOE and "
                "Alzheimer's disease. I don't have sufficient indexed "
                f"evidence to answer this {topic} question reliably."
            ),
            "agent_log": state.get("agent_log", []) + [
                "Clarification Agent: topic is outside the indexed collection."
            ],
        }

    return {
        **defaults,
        "agent_log": state.get("agent_log", []) + [
            "Clarification Agent: question accepted."
        ],
    }
