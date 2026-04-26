---
name: error-taxonomy-generator
description: Generate a root-cause-level error taxonomy for GenAI systems.
  Use when given a PRD, technical design, and qualitative notes
  to structure failure modes for evaluation design.
metadata:
  arguments: "--prd <docs/prd.md> --technical_design <docs/design.md> --notes <docs/notes.md>"
---

# Error Taxonomy Generator

## Overview

Use this skill to create a practical error taxonomy for a text-based GenAI product such as a chatbot, RAG application, or agentic system.

The purpose of this skill is to:
- turn qualitative evaluation evidence into a structured error taxonomy
- organize failure modes at the **root-cause level**
- make the taxonomy as mutually exclusive and collectively exhaustive as practical
- assign priorities based on severity and recurrence
- include representative examples for each error type
- identify which error types are likely in scope for later quantitative evaluation
- explicitly note where evidence is sparse, ambiguous, or insufficient

This skill is for **taxonomy creation only**. It should not design quantitative metrics, choose evaluators, define thresholds, or produce monitoring plans.

---

## Inputs Required

- `prd`: The path to the product requirements file
- `technical_design`: The path to the technical design file
- `notes`: The path to the qualitative open-coding notes file

## How to Access Inputs

- Open and read the PRD file from the provided path
- Open and read the technical design file
- Open and read the qualitative notes file
- Use all three sources jointly to inform taxonomy construction

---

## Instructions

### Step 1: Read product context

From the PRD, extract and summarize:
- intended user value
- intended use cases
- unsupported or out-of-scope cases
- major safety / guardrail expectations
- major launch-critical risks

### Step 2: Read the technical design

Identify:
- major system components
- likely root-cause zones
- architecture-specific failure modes

Examples:
- RAG systems: retrieval, grounding, citation support
- agentic systems: routing, tool choice, tool execution, handoffs, recovery
- plain LLM systems: instruction handling, scope control, policy handling, context handling

### Step 3: Read qualitative open-coding notes

Identify:
- repeated failure patterns
- repeated likely causes
- representative examples
- disagreements or ambiguities in labeling
- areas where evidence is thin

### Step 4: Cluster failures into root-cause groups

Group observations into candidate root-cause categories.

Use the technical design to avoid grouping together failures that appear similar but arise from different system causes.

### Step 5: Organize into a taxonomy

Each error type must include:
- definition
- examples
- priority
- likely system area
- whether it is in scope for quantitative evaluation

### Step 6: Assign priority

Assign:
- `P0`: severe, safety-critical, or launch-blocking
- `P1`: important and recurring
- `P2`: lower priority or exploratory

Use both severity and recurrence.

If recurrence is unknown but severity is high, it can still be `P0`.

### Step 7: Check taxonomy coverage

Evaluate whether the taxonomy covers:
- core product behavior risks
- safety / guardrail risks
- architecture-specific failure modes
- out-of-scope or refusal failures
- known high-risk use cases

Mark each area as:
- `covered`
- `partially_covered`
- `not_covered`

### Step 8: Note ambiguity explicitly

List unresolved or ambiguous areas.

Examples:
- insufficient evidence to separate categories
- unclear root cause (retrieval vs generation)
- unknown severity due to missing usage frequency

Do not force artificial clarity.

---

## Output Format

Return ONLY valid JSON. Do not include explanations outside JSON.

```json
{
  "error_taxonomy": [
    {
      "error_type": "string",
      "description": "string",
      "priority": "P0 | P1 | P2",
      "examples": ["string"],
      "likely_system_area": "string or null",
      "in_scope_for_quantitative_eval": true
    }
  ],
  "taxonomy_coverage_notes": [
    {
      "area": "string",
      "status": "covered | partially_covered | not_covered",
      "notes": "string"
    }
  ],
  "unresolved_or_ambiguous_areas": [
    {
      "issue": "string",
      "why_ambiguous": "string",
      "recommended_next_step": "string"
    }
  ]
}
```

---

## Taxonomy Design Principles

1. Build a root-cause-level taxonomy, not a symptom-level taxonomy
2. Make the taxonomy as MECE as practical
3. Prefer actionable and recurring categories
4. Do not invent artificial precision when evidence is weak
5. Include representative examples for each error type
6. Mark whether each error type is suitable for quantitative evaluation
7. Preserve ambiguity when evidence is insufficient

---

## Taxonomy Quality Checks

### 1) Duplicate or overlapping categories
Avoid categories that represent the same root cause

### 2) Categories that are too broad
Example: `reasoning_failure`

Split into operational subtypes if needed

### 3) Categories that are too narrow
Avoid overly specific categories that will not recur

### 4) Mixing abstraction layers
Do not mix:
- root causes
- symptoms
- business outcomes

### 5) Unsupported categories
Do not introduce categories not grounded in:
- qualitative notes
- PRD risks
- technical design

### 6) Missing major risk areas
Ensure coverage of:
- intended use cases
- out-of-scope scenarios
- safety and guardrails
- architecture-specific risks

### 7) Sparse evidence
Explicitly state when evidence is insufficient

"Not enough evidence" is acceptable

---

## Example Structure

- retrieval
  - retrieval_miss
  - retrieval_irrelevance
- tool_use
  - tool_selection_error
  - tool_execution_failure
- policy_handling
  - refusal_logic_failure
  - unsafe_policy_bypass

