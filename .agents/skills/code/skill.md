# Alfred System Capabilities and Skill Manifest

This document defines the behavioral specifications, intent routing protocols, and tool execution matrices for the Alfred Task Orchestration System.

## 1. Core Competency Matrix

The agent operates across a defined tier-based classification protocol to govern task execution and resource allocation.

### Tier 1: Personal Well-Being (Priority Score: 10)
Core focus areas encompass health, family engagement, wellness routines, and habit tracking. The system mandates immediate processing of these tasks before addressing lower-priority tiers.

### Tier 2: Professional Obligations (Priority Score: 5)
Core focus areas encompass enterprise meetings, corporate communications, schedule management, and professional deliverables.

### Unclassified Tasks (Priority Score: 0)
General tasks lacking definitive actionable parameters, such as passive information tracking or non-specific general chores.

---

## 2. Intent Routing and Agent Dispatch Protocol

When a task string enters the orchestration loop, keyword analysis assigns the workload to specialized sub-agents.

| Agent Name | Target Intent | Authorized System Tool |
| :--- | :--- | :--- |
| meeting_agent | Corporate calendars, event coordination, time slots | schedule_event |
| email_agent | Communication dispatch, follow-ups, message drafting | send_email, draft_reply |
| habit_agent | Wellness routines, health reminders, recurring actions | set_reminder |
| knowledge_agent | User preferences, preference archival, data lookups | add_to_kb |

---

## 3. Operational Logic Flows

### Policy Execution Flow
1. Parsing: The system converts raw input strings into discrete task dictionaries with unique tracking IDs.
2. Classification: The internal router assigns a tier rating and an algorithmic priority score based on intent definitions.
3. Priority Check: If a multi-task queue contains both Tier 1 and Tier 2 objectives, the execution loop enforces the Alfred Protocol by processing Tier 1 items first.
4. Tool Selection: The orchestrator maps the matched sub-agent to its exact permitted API tool.
5. Verification: Parameters undergo structural verification against the tool's required schema before executing exterior API calls.

---

## 4. Reinforcement Learning Reward Rubric

The underlying policy model optimizes its text output based on five foundational criteria during Group Relative Policy Optimization (GRPO):

1. Priority Ordering (25%): Absolute enforcement of Tier 1 processing ahead of Tier 2 items.
2. Correct Routing (20%): Accurate matching between task text intent and the assigned sub-agent.
3. Action Completeness (20%): Formatting the JSON string with all mandatory arguments required by the target schema.
4. API Call Success (20%): Avoiding run-time failures and schema exceptions when engaging external interfaces.
5. No Over-Triggering (15%): Refraining from tool execution when handling non-actionable or unclassified text input.
