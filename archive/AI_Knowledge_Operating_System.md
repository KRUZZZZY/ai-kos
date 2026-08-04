# AI Knowledge Operating System

## Overview

This system is a personal knowledge operating system combining:

-   Local LLMs
-   Obsidian
-   Hermes reasoning
-   RAG retrieval
-   Knowledge consolidation
-   Structured templates
-   AI metadata
-   Human-readable articles

The goal is persistent, evolving knowledge rather than transient chat
history.

------------------------------------------------------------------------

# Core Principles

1.  Raw information is not knowledge.
2.  Knowledge should be consolidated.
3.  AI and humans need different views of information.
4.  Retrieval should minimize token usage.
5.  Knowledge should evolve over time.
6.  Templates become procedural memory.
7.  Humans remain in control.

------------------------------------------------------------------------

# Hardware

-   Ubuntu Linux
-   RTX 5070 Ti
-   16 GB RAM minimum
-   32 GB RAM recommended
-   NVMe SSD

------------------------------------------------------------------------

# Software Stack

## Inference Layer

-   Ollama
-   DeepSeek
-   Qwen
-   Additional models as required

## Reasoning Layer

-   Hermes

## Knowledge Layer

-   Obsidian

## Retrieval Layer

-   Vector database
-   RAG system

## User Interface

-   Open WebUI or custom Hermes interface

------------------------------------------------------------------------

# Memory Layers

## Inbox

Temporary material.

## Backlog

Unconsolidated sessions.

## Episodic Memory

Research sessions, debugging sessions, conversations.

## Semantic Memory

Knowledge articles.

## Procedural Memory

Templates.

## Executive Memory

Indexes, summaries, concept maps.

------------------------------------------------------------------------

# Knowledge Pipeline

Raw Material → Backlog → Consolidation → Articles → Summaries → Indexes
→ Retrieval → Hermes

------------------------------------------------------------------------

# Nightly Consolidation

1.  Read backlog.
2.  Detect topics.
3.  Merge duplicates.
4.  Update articles.
5.  Generate summaries.
6.  Update metadata.
7.  Update embeddings.
8.  Generate indexes.
9.  Archive processed material.

------------------------------------------------------------------------

# Weekly Consolidation

-   Review templates.
-   Detect repeated structures.
-   Suggest schema changes.
-   Merge related concepts.
-   Update relationships.

------------------------------------------------------------------------

# Context Rot Prevention

Articles have:

-   Limited scope.
-   Limited concepts.
-   Soft cap of 10 sections.
-   Topic separation.

Large topics become multiple articles.

------------------------------------------------------------------------

# Multi-Level Summaries

-   Section summary
-   Article summary
-   Category summary
-   Domain summary

Hermes descends through these levels as required.

------------------------------------------------------------------------

# Dual-Layer Articles

## AI Layer

-   summary
-   dependencies
-   confidence
-   importance
-   keywords
-   related concepts
-   template

## Human Layer

-   explanations
-   examples
-   references
-   diagrams
-   code

------------------------------------------------------------------------

# Templates

Examples:

-   Concept
-   Programming concept
-   Project
-   Research paper
-   Process
-   Decision
-   Problem

Templates reduce token usage.

------------------------------------------------------------------------

# Template Evolution

Weekly scans identify common structures.

New templates may be proposed and existing articles migrated.

Templates become procedural memory.

------------------------------------------------------------------------

# Example Metadata

``` yaml
template: programming_concept
importance: high
confidence: 0.9
depends_on:
  - Prolog
related:
  - Parsing
summary: Declarative grammar rules.
```

------------------------------------------------------------------------

# Folder Structure

vault/

-   inbox/
-   backlog/
-   episodes/
-   knowledge/
-   concepts/
-   summaries/
-   indexes/
-   templates/
-   archive/

------------------------------------------------------------------------

# Retrieval Strategy

1.  Search summaries.
2.  Search metadata.
3.  Search articles.
4.  Search source material.

Only retrieve what is necessary.

------------------------------------------------------------------------

# Agent Responsibilities

-   Ingest material.
-   Summarize information.
-   Update articles.
-   Suggest templates.
-   Detect contradictions.

Humans approve major changes.

------------------------------------------------------------------------

# Long-Term Goal

A personal knowledge operating system consisting of:

-   Obsidian as the knowledge layer.
-   Hermes as the reasoning layer.
-   Templates as procedural memory.
-   Articles as semantic memory.
-   Backlogs as episodic memory.
-   Summaries as compression.

The result is an evolving AI-assisted knowledge system.
