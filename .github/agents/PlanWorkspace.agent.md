---
name: PlanWorkspace
description: (Workspace) Researches and outlines multi-step plans
argument-hint: Outline the goal or problem to research
tools:
  - search
  - agent
  - search/usages
  - read/problems
  - search/changes
  - execute/testFailure
  - web/fetch
  - web/githubRepo
handoffs:
  - label: Start Implementation
    agent: agent
    prompt: Start implementation
  - label: Open in Editor
    agent: agent
    prompt: '#createFile the plan as is into an untitled file (`untitled:plan-${camelCaseName}.prompt.md` without frontmatter) for further refinement.'
    showContinueOn: false
    send: true
---

# Plan (Workspace)

Describe aquí el objetivo y el contexto; este agente devuelve un plan accionable.
