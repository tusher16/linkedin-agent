# My Content Ideas & Context
# ============================================================
# This file is YOUR brain dump. The agent reads this before generating posts.
# Update this whenever you have new ideas, finish a paper review, or
# make progress on your thesis.
#
# The agent will NEVER generate random topics. It uses THIS file as its source.
# ============================================================

## About Me
- Name: Mohammad Obaidullah Tusher
- Role: AI Engineer | Data Engineer | ML Researcher
- Location: Berlin, Germany
- Focus Areas: AI Engineering (RAG, Autonomous Agents, LLM Fine-tuning), MLOps, Machine Learning (Computer Vision, NLP), Data Engineering (ETL, AWS, Airflow).
- Current Goal: Building a personal brand to share insights on data engineering, machine learning research, and cloud architecture.

## Current Thesis Work
- Topic: Semantic Segmentation of Historical Legal Documents (developing an end-to-end LayoutLMv3 pipeline).
- Key findings so far: Built a custom 18-class segmentation system. I've also incorporated the latest LLM fine-tuning techniques on domain-specific data and applied rigorous MLOps practices to track model iterations.
- Challenges you're facing: Handling severe class imbalance with Transfer Learning; building a robust, production-ready MLOps data pipeline integrating Tesseract OCR and advanced prompt engineering / RAG flows.

## Past Projects & Experience
- Home24 SE (Business Analytics): Boosted conversion by 10% through a custom Python/Airflow data pipeline; optimized AWS Redshift SQL models; conducted NLP sentiment analysis on customer reviews.
- Gigabyte (Full-Stack Data Scientist): Achieved 95% forecast accuracy for new product launches with Scikit-learn predictive models; engineered end-to-end pipelines for gaming community data.
- ID Document Processing Pipeline: Engineered a modular pipeline (Classification -> Segmentation -> Deskew -> Cleaning) using Keras and OpenCV for Tesseract OCR.

## Publications & Papers
- Paper: Development of an Expert System-Oriented Service Support Help Desk Management System (2019)
  Authors: Abrar Hasin Kamal, Mohammad Obaidullah Tusher, Shadman Fahim Ahmad, Nusrat Jahan Farin, Nafees Mansoor
  Key insight: Explored expert system management architectures.
  My take: It was a great foundation in structured service-oriented systems.

- Paper: DEB: A Delay and Energy-Based Routing Protocol for Cognitive Radio Ad Hoc Networks (2020)
  Authors: Sumaiya Tasmim, Abrar Hasin Kamal, Mohammad Obaidullah Tusher, Nafees Mansoor
  Key insight: Energy and delay optimization in ad hoc networks.
  My take: Showcased early algorithmic research skills for optimizing networking infrastructure.

## Post Ideas Backlog
- [ ] Idea: Building reliable RAG systems vs. Fine-Tuning LLMs: Lessons learned from my thesis architecture.
- [ ] Idea: Deep dive into building custom AI Agents and why strict MLOps tracking makes or breaks them.
- [ ] Idea: How I optimized AWS Redshift pipelines at Home24 to speed up business intelligence dashboards.
- [ ] Idea: Overcoming class imbalance in Computer Vision: Why I used Focal Loss for my LayoutLMv3 Master's thesis.
- [ ] Idea: The difference between academic ML research and building end-to-end data pipelines for production (ELT, Airflow, Terraform).
- [ ] Idea: Extracting data from noisy OCR: Lessons learned from my university document automation project.

## Published Writing Samples
Full text of past articles is in writing/context/ — the RAG indexer reads these.

- writing/context/2021-django-portfolio-part1.md — Django 3.2 portfolio site (Part 1): Python setup, MySQL, virtualenv, git, Django project skeleton
- writing/context/2021-django-portfolio-part2.md — Django 3.2 portfolio site (Part 2): Bootstrap templates, static files, template inheritance, django-active-link
- writing/context/2021-git-cheatsheet.md — "Understand git in 4min": beginner-friendly git cheatsheet covering init, clone, branches, merge, push, delete
- writing/context/2023-reddit-data-engineering.md — End-to-end data engineering: Reddit API → AWS S3 → Redshift → Tableau, orchestrated with Airflow in Docker, infra via Terraform

Writing patterns from these articles to match:
- Step-by-step technical walkthroughs with exact commands
- Explains the WHY before the HOW
- Honest about what went wrong ("port 3306 was blocked, I raised a support ticket")
- Links to official docs rather than paraphrasing them
- Practical over theoretical — shows real output/screenshots as checkpoints
- Ends sections with "now we can move to the next part" style transitions

## My Writing Style Preferences

### Tone and voice
- Professional, technical but accessible, analytical, and insightful.
- Things I NEVER want: overly generic motivational quotes, too many emojis, buzzwords without substance, vague claims like "powerful" or "seamless".
- Things I ALWAYS want: concrete technical details (specific tools, versions, commands), actionable takeaways, honest reflections on engineering challenges and failures.

### 2026-level technical writing standard
My Medium blog for the LinkedIn agent project should be written at the level of senior AI engineering content in 2026 — not a beginner tutorial, not a hype piece. Every article must have:

**Problem statement first**
- Open with the exact problem being solved and why existing solutions fall short.
- Be specific: not "AI content is bad" but "LLM-generated LinkedIn posts have no personal voice because they have no personal context, and re-draft loops without a quality gate ship garbage."

**Architecture before code**
- Explain the full architecture decision before showing any implementation.
- For every major component: what it is, why this one over alternatives (ADR-style), how it fits into the larger system.
- Include real diagrams or ASCII diagrams, not just prose.
- Mention the LangGraph StateGraph, the six bounded units (schemas, tools, graph, api, db, dashboard), the data flow from topic → guardrails → outline → human approval → draft → review → publish.

**RAG and vector database — full depth**
- Explain what pgvector is and why it was chosen over Qdrant (single DB, no extra infrastructure).
- Explain the full RAG pipeline: chunk my_context.md → embed with text-embedding-3-small → upsert into pgvector → cosine similarity search at generation time.
- Explain why static context loading (just reading a file) is worse than retrieval — relevance, token efficiency, scalability.
- Show the recall@3 eval as the quality gate.

**Agent architecture — full depth**
- Explain LangGraph StateGraph honestly: it is not magic, it is a directed graph of node functions with typed state.
- Explain the iteration cap (≤2 re-drafts) and cost cap ($0.05/run) and why they exist — bounded loops prevent infinite spend.
- Explain human-in-the-loop interrupt — why keeping a human approval step is the right call even in an "autonomous" agent.
- Explain the guardrails node — prompt injection detection before any LLM call.

**Knowledge graph context (graphify)**
- Explain that graphify builds a persistent knowledge graph of the project (102 nodes, 130 edges, 14 communities) from code + docs.
- Explain the god nodes (LinkedIn AI Agent, TASK.md, Design Spec) as the architectural spine.
- Explain how the graph is used for context across sessions — not just RAG but structural understanding.

**Eval pipeline — the centerpiece**
- Cross-model evaluation: Gemini 2.5 Flash drafts, GPT-4o-mini judges. Never the same model judging its own output.
- 4 criteria: tone match, technical density, hook strength, AI-cliché detection.
- 15-topic baseline dataset versioned in LangSmith.
- Show real numbers. If baseline is below 7, say so and explain what was done.

**Project structure — show it explicitly**
- Always include the directory tree so readers can orient themselves.
- Explain every top-level folder's responsibility in one sentence.
- Link to the GitHub repo.

**Honest about AI-assisted development**
- I used Claude Code (AI coding assistant) to write the majority of the implementation code.
- Be transparent about this: what the AI did well (boilerplate, schema generation, test scaffolding), what needed human judgment (architecture decisions, eval design, ADR trade-offs).
- The point is not "I wrote every line" — the point is "I designed the system, made every architectural decision, and validated every output."
- This is the honest 2026 way to write about AI-assisted engineering. Hiding it is worse.

**Scope and outcomes — always close the loop**
- Every article ends with: what was the scope of this day/section, what was actually built, what test gate confirmed it works.
- Include real numbers wherever possible: coverage %, eval score, latency, token cost per run.
- Be honest about what is not done yet and why (kill-switch cuts, v2 roadmap items).
- The outcome section should answer: "if I read only this section, do I know what was shipped and whether it works?"
