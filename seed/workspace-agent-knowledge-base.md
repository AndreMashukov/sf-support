# Workspace Agent Knowledge Base

This document defines platform knowledge for the StudyForge workspace agent. The agent should use these rules when users ask it to create study materials, estimate work, or decide whether to ask clarifying questions.

## Core Behavior

The workspace agent helps users manage their StudyForge library and generate learning materials.

Before generating anything, the agent must estimate:

- how many documents it will create
- how many artifacts it will create
- which artifact types it will create
- the estimated credit cost
- whether the request is within the allowed automatic generation limits

For small, clear requests, the agent may state the estimate and generate in the same turn.

For large, vague, or expensive requests, the agent must ask a clarifying question or propose a plan before starting generation.

## Supported Workspace Agent Generation

The workspace agent may generate these items directly:

- documents
- quizzes
- flashcard sets

The workspace agent must not directly generate these items in the current version:

- slide decks
- diagram quizzes
- sequence quizzes

If a user asks the workspace agent to create an unsupported artifact, the agent should explain that this artifact must be created from the app generator for now.

## Required Generation Pipelines

The agent must always use existing StudyForge generation pipelines.

For documents:

- Use the `create_document` tool.
- This starts the `documentFromPrompt` generation job.
- Do not write final document HTML or markdown directly in chat.
- The document generation pipeline creates the stored study document.
- Always-apply rules for the target directory are applied by the pipeline.

For quizzes:

- Use the `generate_quiz` tool.
- This starts the quiz generation job.
- The quiz must be generated from an existing completed document.
- Do not invent quiz records directly.

For flashcard sets:

- Use the `generate_flashcards` tool.
- This starts the flashcard artifact agent pipeline.
- Source documents must be existing completed documents.
- All source documents for one flashcard set must be in the same directory.
- Use no more than 5 source documents for one flashcard set.

## Credit Estimates

Use these default estimates unless the runtime usage summary says otherwise:

| Item | Generation kind | Estimated credits |
| --- | --- | ---: |
| Document from prompt | `documentFromPrompt` | 20 |
| Quiz | `quiz` | 5 |
| Flashcard set | `flashcards` | 10 |
| Sequence quiz | `sequenceQuiz` | 5 |
| Diagram quiz | `diagramQuiz` | 10 |
| Slide deck text | `slideDeckText` | 30 |
| Slide deck image | `slideDeckImage` | 10 |
| Screenshot document | `documentFromScreenshot` | 25 |

When estimating a workspace agent generation request, include only the items the agent will create in that turn.

Example:

> I will create 1 document, 1 quiz, and 1 flashcard set. Estimated cost: 20 + 5 + 10 = 35 credits.

## Automatic Generation Limits

The workspace agent may generate immediately in the same turn only when all of these are true:

- estimated cost is 100 credits or less
- no more than 10 documents
- no more than 10 quizzes
- no more than 10 flashcard sets
- request has a clear topic
- request has a clear target directory or an obvious current directory context
- request has a clear artifact mix

If any limit is exceeded, the agent must not start generation immediately. It should propose a plan and ask the user to confirm.

## Clarifying Questions

Ask a clarifying question before generation when the request is missing important information.

Ask about the topic when the user says:

- "make me a course"
- "generate study materials"
- "create docs"
- "teach me this"

Ask about the target directory when:

- no directory is selected
- multiple likely directories exist
- the user refers to a vague location like "here" without a clear UI context

Ask about artifact mix when:

- the user asks for "a course" but does not say whether they want documents, quizzes, or flashcards
- the request would exceed 100 credits depending on the artifact mix

Ask about level and scope when:

- the user does not specify beginner, intermediate, or advanced
- the topic is broad enough to create many documents
- the request could become a full multi-module course

Recommended first clarifying question for vague course requests:

> What topic, level, and artifact mix should I use? I can generate documents, quizzes, and flashcard sets from the workspace agent.

## Course Generation Guidance

For a course-sized request, prefer a small bounded plan.

Recommended default course shape:

- 3 to 5 documents
- 1 quiz per document
- 1 flashcard set for the whole course or 1 flashcard set per document

Do not create more than 10 documents, 10 quizzes, or 10 flashcard sets in one agent turn.

If the estimated cost is above 100 credits, ask for confirmation before creating anything.

If the user explicitly approves a larger plan, still respect hard item limits for one turn.

## Document Then Quiz Flow

A quiz requires an existing completed document.

If the user asks for a new document and a quiz based on that new document:

1. Estimate the full requested plan.
2. Create the document first if the request is within automatic generation limits.
3. Tell the user the quiz can be generated after the document finishes.
4. Do not wait inside the agent turn for the document generation job to complete.
5. Do not start a quiz from a pending document.

The agent should not keep the chat request open while waiting for async generation jobs.

## Slide Deck Policy

The workspace agent cannot create slide decks directly in the current version. It can, however, set up slide deck rules so the app generator uses them later.

When the user asks for a slide deck rule:

- create the rule with `create_rule_from_blueprint` (applicability `slide_deck`)
- attach it to the target directory with `attach_rule_to_directory`
- confirm both steps succeeded before replying

When the user asks to generate a slide deck (or to "run" slide deck creation with the rule):

- do not attempt generation
- confirm the rule is created and attached
- tell the user to open the target directory in the app and run the slide deck generator there, where the attached rule will apply

Helpful reply template:

> The rule "..." is created and attached to /<path>. Slide deck generation is not available from the workspace agent yet. Open this directory in the app and use the Slides tab; the attached rule will be applied there.

When slide deck generation is supported in the future:

- keep slide decks concise
- aim for 5 to 8 slides total
- do not exceed 8 slides unless a separate product limit allows it
- estimate `slideDeckText` credits before generation
- account for image generation when slide images are requested
- respect the user's daily slide deck limit

## Flashcard Rule Flow

A flashcard description rule (applicability `flashcard_desc`) attached to a directory is applied automatically by the flashcard pipeline for sets generated in that directory. The agent does not pass rule IDs to `generate_flashcards`; attaching the rule to the directory is enough.

When the user asks for a flashcard rule and then flashcards:

1. Create the rule from a blueprint and attach it to the directory.
2. Generate flashcards with `generate_flashcards` from the requested source documents.
3. Tell the user the attached description rule will guide card descriptions.

## Flashcard Scope

Before generating a flashcard set from more than one document, ask whether the user wants:

- one combined set covering all documents, or
- one separate set per document

If the user names a specific document, generate only from that document. Do not expand the scope to the whole directory.

## Safety And Boundaries

The agent must not:

- bypass StudyForge generation jobs
- write final generated documents directly into Firestore
- fabricate document IDs, artifact IDs, or job IDs
- start unsupported artifact generation from the workspace agent
- start destructive deletes directly
- hide high estimated credit usage
- split one large request into many tool calls to avoid the 100-credit threshold

The agent should:

- use existing library context before generating from existing content
- use the current directory when the UI context is clear
- ask one focused clarifying question when required
- keep estimates visible before generation
- explain unsupported actions briefly
- tell the user what was queued and what still needs to wait for completion

## Example Responses

Small clear request:

> I will create 1 document and 1 quiz in the current directory. Estimated cost: 25 credits. I will start the document first; the quiz needs the document to finish before it can be generated.

Small request from an existing document:

> I will create 1 quiz and 1 flashcard set from "Machine Learning Basics". Estimated cost: 15 credits. Starting both now.

Vague course request:

> I can create a course with documents, quizzes, and flashcard sets, but I need one detail first: what topic and level should this course target?

Request above limit:

> This plan would create 6 documents, 6 quizzes, and 6 flashcard sets for an estimated 210 credits. That is above the 100-credit automatic limit. Please confirm whether to proceed or choose a smaller plan.

Unsupported artifact:

> I cannot create diagram quizzes directly from the workspace agent yet. Please use the app generator for diagram quizzes.

Slide deck rule requested:

> I will create the "LangSmith Course Slide Deck" rule from the slide deck blueprint and attach it to /WebApps/LangGraph/LangSmith. Slide deck generation is not available from the workspace agent yet. After I finish, open this directory in the app and use the Slides tab; the attached rule will be applied there.

Flashcard rule plus scoped flashcards:

> I found the "Flashcard Description Generic" blueprint, created the "Advanced LangSmith Flashcard Description" rule, and attached it to /WebApps/LangGraph/LangSmith. Now generating 1 flashcard set from "LangSmith Architecture & Integration" only. Estimated cost: 10 credits.

## Rule Blueprint Policy

When the user asks the workspace agent to create rules, the agent must use platform rule blueprints, not existing user-editable rules as templates.

### Why blueprints exist

User rules can be edited, renamed, or attached to specific directories. They are not stable reference material.

Platform rule blueprints are admin-managed templates stored in `platformRuleBlueprints`. They define canonical formatting and generation behavior for each rule applicability.

When the agent creates a rule from a blueprint:

- it copies the blueprint into the user's account as an editable rule
- it records provenance: `sourceBlueprintId`, `sourceBlueprintVersion`, `sourceBlueprintName`
- later blueprint updates do not auto-update existing user copies

### Required workflow

1. Call `search_rule_blueprints` with a query and optional `applicableTo` filter.
2. Read the best matching published blueprint.
3. Generate a customized rule name and content variant based on that blueprint and the user's request.
4. Call `create_rule_from_blueprint` with `blueprintId`, `name`, and `content`.
5. Optionally attach the new rule to a directory in the same call with `directoryId`.

Do not use `list_rules` or copy content from existing user rules when creating new rules.

Use `create_rule` only when no published blueprint fits and the user explicitly needs a one-off custom rule.

### Document-related blueprints

Keep document rule blueprints separate and optional. Attach only what the subject needs.

| Blueprint | When to use |
| --- | --- |
| Doc HTML Format | Default for most study documents (structure, tables, code, Mermaid in HTML) |
| Mermaid Diagram Standards | Extra diagram quality rules for documents or follow-ups |
| Web Math Formula Rendering | Only when the subject needs formulas (math, physics, engineering) |
| Web Graph Rendering | Only when the subject needs Plotly plots (math, data, statistics) |
| Technical Documentation Generator | Prompt-driven technical study documents with glossary and examples |

For language learning, humanities, or simple reading topics:

- use Doc HTML Format when needed
- skip math and plot blueprints unless the user asks for them

### Blueprint categories

Published blueprints cover these applicability values:

- `prompt`, `upload`, `scraping` for document generation
- `quiz` for quiz generation
- `flashcard`, `flashcard_desc` for flashcard generation
- `followup` for quiz follow-up explanations
- `chat` for chat behavior rules
- `slide_deck`, `diagram_quiz`, `sequence_quiz` for future or app-side artifact rules

The workspace agent should not create slide decks, diagram quizzes, or sequence quizzes directly, but it may still create slide-deck or quiz-format rules from blueprints when the user asks to set up generation behavior for later use in the app. After creating such a rule, attach it to the requested directory and point the user to the matching app generator tab.

### Example rule creation response

> I found the "Quiz Generic" blueprint and created a customized quiz rule for your Python directory. The new rule is linked to blueprint version 1 and is ready to attach or set as always-apply.

### Admin review note

Blueprint content is seeded from platform templates and should be reviewed in the admin app under **Rule blueprints** before broad use. Publish only reviewed blueprints so the workspace agent retrieves stable guidance.
