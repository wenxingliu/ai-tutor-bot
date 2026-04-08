# Chemistry Course AI Tutor --- Product Requirements Document (v1)

## 1. Purpose

Build a simple AI tutor for a university chemistry course. The tutor
should answer student questions using only the course PDF materials
stored in a vector database. The system should refuse out-of-scope
questions and academic-integrity violations through instructions in the
LLM system prompt.

## 2. Scope

### In scope

-   Answer chemistry questions based on uploaded course PDFs.
-   Retrieve relevant document chunks from a single vector store.
-   Use one LLM to generate tutor responses.
-   Enforce in-scope and academic-integrity behavior through the LLM
    system prompt.
-   Support PDF re-upload and re-indexing.

### Out of scope for v1

-   Web browsing.
-   Multi-course support.
-   Memory across users.
-   Final post-generation safety checker.
-   Instructor analytics.
-   Multiple vector databases.
-   Multi-agent orchestration.

## 3. Product Requirements

### Functional requirements

1.  Upload one or more PDF course files.
2.  Store the files in a single vector store.
3.  Retrieve the top relevant chunks for each user question.
4.  Send the retrieved chunks and the question to the tutor model.
5.  Refuse questions that are unrelated to the course.
6.  Refuse requests that violate academic integrity.
7.  Return a fallback response when the knowledge base does not contain
    enough information.

### Non-functional requirements

-   Keep the system simple and easy to maintain.
-   Minimize latency and token usage.
-   Keep prompts deterministic and narrow in scope.
-   Log key events for debugging.

## 4. UI Requirements

-   Chat interface with message history
-   Input box + send button
-   Loading indicator
-   Optional source display

## 5. Definition of Done

-   Answers chemistry questions correctly
-   Refuses unsafe/out-of-scope queries
-   PDFs are retrievable
-   API endpoints are stable and documented
