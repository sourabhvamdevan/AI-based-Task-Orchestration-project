
# AI hackathon submission (Task Orchestrator using AI)

Alfred is a multi-agent reinforcement learning environment built on the Model Context Protocol (MCP). It is designed to train large language models (LLMs) to prioritize personal well-being over professional obligations using the Alfred Protocol.

## Project Overview

The project utilizes Group Relative Policy Optimization (GRPO) to fine-tune an agent that intelligently manages a task queue. The core logic ensures that health, family, and wellness tasks (Tier 1) are always addressed before work-related meetings or emails (Tier 2).

## Core Components

### 1. Orchestrator
The central routing layer that classifies incoming tasks by tier and routes them to the appropriate sub-agent based on keyword scanning.

### 2. Specialized Agents
* Meeting Agent: Manages Google Calendar scheduling and event logistics.
* Email Agent: Handles Gmail communications and draft generation.
* Habit Agent: Establishes recurring reminders for wellness and routines.
* Knowledge Agent: Manages the personal knowledge base and user preferences.

### 3. RL Environment
A custom environment that provides observations of the task queue and calculates rewards based on a strict priority rubric.

## Technical Stack

* Framework: Python 3.11
* Interface: Gradio
* Training: Unsloth + TRL (GRPO)
* APIs: Google Calendar API, Gmail API
* Data: Synthetic episode generation for robust policy learning

## Installation

1. Clone the repository:
   git clone <https://github.com/sourabhvamdevan/AI-based-Task-Orchestration-project>
   cd alfred-openenv

2. Install dependencies:
   pip install -r requirements.txt

3. Configure environment variables:
   Create a .env file with your credentials:
   HF_TOKEN=<your-token>
   GOOGLE_CREDENTIALS_JSON=<path-to-json>

## Usage

### Running the Interface
To launch the Gradio orchestration dashboard:
python app.py

### Training the Agent
To start the GRPO training cycle:
python training.py

### Inference and Comparison
To run a trained model against the baseline:
python inference.py --model <path-to-model> --compare

## Priority Rubric

Alfred follows a 5-component reward system:
1. Priority Ordering: tier 1 tasks processed before tier 2.
2. Correct Routing: Accurate assignment of tasks to specialized agents.
3. Action Completeness: Ensuring all mandatory tool parameters are provided.
4. API Call Success: Successful execution of integrated tools.
5. No Over-Triggering: Correct abstention from non-actionable tasks.

