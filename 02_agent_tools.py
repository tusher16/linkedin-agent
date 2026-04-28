"""
Phase 3: Agent Tools (v2)

Architecture change: The agent now reads YOUR personal context before doing anything.
It also generates a cheap outline first so you can approve before spending tokens on a full draft.

Pipeline: Load Context → Plan Outline → [You Approve] → Draft Full Post → Review → Publish
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

CONTEXT_FILE = Path(__file__).parent / "my_context.md"


def load_my_context() -> str:
    """Read the personal context file. This is not a tool — it's a helper
    that every tool calls internally to ground the agent in YOUR world."""
    if not CONTEXT_FILE.exists():
        return "No personal context found. Create my_context.md to personalize outputs."
    return CONTEXT_FILE.read_text()


# ---------------------------------------------------------------------------
# Tool 1: Plan Post Outline
# ---------------------------------------------------------------------------
# WHY: Full post generation costs ~1000+ tokens. An outline costs ~200.
# You see the structure first, reject what you don't like, and only THEN
# spend tokens on the full draft. This saves money and gives you control.
# ---------------------------------------------------------------------------

@tool
def plan_post_outline(idea: str) -> str:
    """Create a quick bullet-point outline for a LinkedIn post BEFORE writing the full draft.

    This is cheap (few tokens). Review the outline first, then call draft_linkedin_post
    with the approved outline.

    Args:
        idea: Your raw idea — can be a sentence, a paper title, a thesis finding, anything.
    """
    context = load_my_context()

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.5, max_output_tokens=300)

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a LinkedIn content strategist. "
         "You have access to the author's personal context below. Use it to make the outline personal and authentic.\n\n"
         "--- AUTHOR CONTEXT ---\n{context}\n--- END CONTEXT ---\n\n"
         "Generate ONLY a brief bullet-point outline (5-7 bullets) for a LinkedIn post. "
         "Include: hook idea, key points, and closing question. "
         "Do NOT write the full post. Keep it under 150 words."),
        ("human", "Create an outline for a post about: {idea}")
    ])

    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"idea": idea, "context": context})


# ---------------------------------------------------------------------------
# Tool 2: Draft Full Post
# ---------------------------------------------------------------------------
# WHY: Now that the user approved the outline, we spend tokens on the real thing.
# The outline + personal context ensures the output matches what they want.
# ---------------------------------------------------------------------------

@tool
def draft_linkedin_post(idea: str, outline: str, tone: str = "professional") -> str:
    """Write the full LinkedIn post based on an approved outline.

    Args:
        idea: The original post idea
        outline: The approved outline from plan_post_outline
        tone: Writing style — professional, casual, storytelling, bold, technical
    """
    context = load_my_context()

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7)

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a LinkedIn ghostwriter for the author below. "
         "Write in THEIR voice using their context. Make it feel personal, not generic.\n\n"
         "--- AUTHOR CONTEXT ---\n{context}\n--- END CONTEXT ---\n\n"
         "Follow this approved outline strictly:\n{outline}\n\n"
         "Rules: "
         "Short paragraphs (1-2 lines). Generous line breaks. "
         "Max 2 hashtags. No cringe motivational quotes. Tone: {tone}"),
        ("human", "Write the full LinkedIn post about: {idea}")
    ])

    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"idea": idea, "outline": outline, "context": context, "tone": tone})


# ---------------------------------------------------------------------------
# Tool 3: Review Post Quality
# ---------------------------------------------------------------------------

@tool
def review_post_quality(draft: str) -> str:
    """Score a LinkedIn post draft on engagement potential. Returns score/10 and feedback."""
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3, max_output_tokens=400)

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You are a LinkedIn content reviewer. Evaluate on: "
         "1) Hook strength 2) Value density 3) Engagement potential 4) Authenticity. "
         "Give a score out of 10 and brief feedback. If score < 7, suggest improvements."),
        ("human", "Review this draft:\n\n{draft}")
    ])

    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"draft": draft})


# ---------------------------------------------------------------------------
# Tool 4: Publish to LinkedIn
# ---------------------------------------------------------------------------

@tool
def publish_to_linkedin(content: str) -> str:
    """Publish a finalized post to LinkedIn via PostBoost API. Only use after approval."""
    api_key = os.getenv("POSTBOOST_API_KEY")
    if not api_key or api_key == "your_postboost_api_key_here":
        return "ERROR: POSTBOOST_API_KEY not configured in .env"

    url = "https://api.postboost.com/v1/posts"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"content": content}

    # MOCK MODE — uncomment when ready to go live:
    # response = requests.post(url, json=payload, headers=headers)
    # response.raise_for_status()
    # return f"Published! Post ID: {response.json().get('id')}"

    return f"[MOCK] Post ready ({len(content)} chars). Uncomment real API call when ready."


# ---------------------------------------------------------------------------
# Test: The full pipeline
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 3 v2: Personal Context + Outline-First Pipeline")
    print("=" * 60)

    # Step 1: Plan (cheap — ~200 tokens)
    print("\n📋 Step 1: Planning outline...")
    outline = plan_post_outline.invoke({
        "idea": "What I learned from reviewing a transformer paper and how it connects to my thesis"
    })
    print(outline)

    # In the real agent, YOU review this outline here and approve/reject.
    # If you reject, no more tokens are spent. That's the whole point.

    print("\n" + "-" * 40)
    input("👆 Review the outline above. Press Enter to approve and generate the full draft...")

    # Step 2: Draft (expensive — only runs after approval)
    print("\n📝 Step 2: Drafting full post from approved outline...")
    draft = draft_linkedin_post.invoke({
        "idea": "What I learned from reviewing a transformer paper and how it connects to my thesis",
        "outline": outline,
        "tone": "storytelling"
    })
    print(draft)

    # Step 3: Review
    print("\n🔍 Step 3: Quality review...")
    review = review_post_quality.invoke({"draft": draft})
    print(review)

    # Step 4: Publish (mocked)
    print("\n🚀 Step 4: Publishing...")
    result = publish_to_linkedin.invoke({"content": draft})
    print(result)
