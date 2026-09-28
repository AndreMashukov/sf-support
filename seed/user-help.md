# Using StudyForge

This article is for **Support "How it works"** answers. It describes what you see in the product and how to use it. It is not the internal guide for the workspace agent.

## Your library

StudyForge stores your study materials in **directories** (folders). Each directory holds documents and related learning items for one subject or project.

- Open a directory to see its documents, quizzes, flashcards, and other artifacts.
- Pick the directory you want before you create or generate new items there.
- If you are not sure which folder to use, choose or create the directory that matches the course or topic.

## Documents

A **document** is a study page (notes, summary, lesson, and similar) stored in a directory.

You can create documents from the web app or ask the **workspace chat** to create one for you. Generation runs in the background. Wait until the document shows as completed before you rely on it for a quiz.

Do not expect a finished document in the same second you submit a request. Refresh the directory or return later if status is still running.

## Quizzes

A **quiz** tests you on an existing **completed document**.

- You cannot build a quiz from a document that is still generating.
- If you want a new document and a quiz on that document, create the document first, wait for it to finish, then create the quiz from that document.

You can create quizzes from the app or ask workspace chat to start quiz generation on a document that is already done.

## Flashcard sets

**Flashcards** help you memorize facts from your documents.

- Flashcards are built from one or more **completed documents** in the **same directory**.
- Use at most five source documents for one flashcard set.
- You can create flashcards from the app or ask workspace chat to generate a set from documents you name.

If a directory has a **flashcard description rule** attached, that rule shapes how card text is written. You do not need to paste the rule yourself; attaching it to the folder is enough.

## Workspace chat

**Workspace chat** is the StudyForge agent in your workspace. It helps you plan work and start generation jobs.

From chat you can usually start:

- new documents
- quizzes (on existing completed documents)
- flashcard sets (from documents in one directory)

Chat **cannot** create these directly in the current product version:

- slide decks
- diagram quizzes
- sequence quizzes

For those, use the matching **generator in the web app** (for example the Slides tab for slide decks).

For large or vague requests (for example "make me a full course"), chat may ask what topic, level, and mix of documents, quizzes, and flashcards you want before it starts. That avoids surprise credit use.

Chat may show an **estimated credit cost** before it starts generation on a clear, small request. If the estimate is high or the request is unclear, it should ask you to confirm or refine the plan first.

## Automatic generation limits (workspace chat)

In one chat turn, workspace chat will only start generation immediately when the plan is small and clear enough. Rough limits:

- estimated cost **100 credits or less**
- at most **10 documents**, **10 quizzes**, and **10 flashcard sets** in that turn
- a clear topic and target directory

If your request is bigger, chat should propose a plan and wait for your confirmation instead of starting everything at once.

## Credit estimates

Credits pay for AI generation. Typical **estimates** for one item (your account may show exact usage elsewhere):

| What you create | Estimated credits |
| --- | ---: |
| Document from a prompt or topic | 20 |
| Quiz | 5 |
| Flashcard set | 10 |
| Sequence quiz (app generator) | 5 |
| Diagram quiz (app generator) | 10 |
| Slide deck text (app generator) | 30 |
| Slide deck image (app generator) | 10 |
| Document from a screenshot (app) | 25 |

Support answers must use numbers from this table or from your in-app usage summary. Support must not invent credit amounts.

When chat quotes a total for several items, it adds the lines for only what it will create in that turn (for example one document plus one quiz: 20 + 5 = 25 credits).

## Slide decks

Slide decks are **not** created from workspace chat today.

If you want slide deck styling rules for a directory, chat can help you create and attach a **slide deck rule** to that folder. To actually **generate** slides, open the directory in the web app and use the **Slides** generator. The attached rule applies there.

## Directory rules

**Rules** on a directory change how generated content looks or behaves (for example document format or flashcard wording).

- Rules attached to a folder apply to new generation in that folder when the product pipeline supports it.
- You manage rules from the app; chat can help create or attach some rule types when you ask.

## Document and quiz rules (line-format)

Some directories use special **line-format** rules (for example one output line per source word with fixed punctuation). If your folder uses one, create or attach the rule to the directory, then generate the document from your source text in the app or via chat. The pipeline applies the rule and checks the shape.

## Getting help in StudyForge

- **How it works** (in Support): product questions answered from Help articles like this one.
- **That helped**: you got your answer; no ticket.
- **Still need help**: opens a support ticket with your question and what Support already tried.
- **Bug**: something is broken; always creates a ticket.
- **Billing**: charges, plans, or credits account questions; always creates a ticket.

Use **Help** in StudyForge web to open Support when the feature is enabled for your environment.

## Common questions

**Why did chat refuse to generate everything at once?**  
Your request may exceed credit or item limits for one turn, or the topic or folder was unclear. Reply with a smaller scope or confirm the plan chat proposes.

**Why can I not quiz this document yet?**  
The document may still be generating or failed. Open the directory and wait until the document is completed, then create the quiz.

**Why can chat not make my slide deck?**  
Use the Slides generator in the app on that directory. Chat can set up rules; generation runs in the app.
