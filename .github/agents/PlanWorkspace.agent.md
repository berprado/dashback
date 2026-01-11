---
name: PlanWorkspace
description: (Workspace) Researches and outlines multi-step plans
argument-hint: Outline the goal or problem to research
tools:
  - search
  - github/get_issue
  - github/get_issue_comments
  - agent
  - search/usages
  - read/problems
  - search/changes
  - execute/testFailure
  - web/fetch
  - web/githubRepo
  - github.vscode-pull-request-github/activePullRequest
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
