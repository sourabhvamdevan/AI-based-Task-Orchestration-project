
import argparse
import json
import random
import sys
from typing import Optional

from env.butler_env import ButlerEnvironment
from env.observation import build_observation_prompt, SYSTEM_PROMPT
from env.action_space import parse_llm_output, validate_action
from agents.orchestrator import Orchestrator
from data.synthetic_todos import generate_episode_queue

def load_model(model_name: str):
    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import torch

        print(f"Status: Loading Alfred Intelligence - {model_name}")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map="auto",
            torch_dtype="auto",
        )
        print(f"Status: Model loaded successfully on device: {model.device}")
        return model, tokenizer

    except Exception as e:
        print(f"Error: Intelligence load failed - {e}")
        print("Status: Falling back to Alfred Simulation Mode.")
        return None, None

def generate_action(model, tokenizer, prompt: str, max_new_tokens: int = 256) -> str:
    if model is None or tokenizer is None:
        return _simulate_action(prompt)

    try:
        import torch

        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                temperature=1.0,
                pad_token_id=tokenizer.eos_token_id,
            )

        input_length = inputs["input_ids"].shape[1]
        generated = tokenizer.decode(
            outputs[0][input_length:], skip_special_tokens=True
        )
        return generated.strip()

    except Exception as e:
        print(f"Error: Neural processing failed - {e}")
        return _simulate_action(prompt)

def _simulate_action(prompt: str) -> str:
    orch = Orchestrator()
    task_text = ""
    for line in prompt.split("\n"):
        if "Handle this task first:" in line:
            task_text = line.split(":", 1)[1].strip()
            break

    if not task_text:
        return json.dumps({
            "tool": "ask_clarification",
            "params": {
                "todo_id": "unknown",
                "field": "task",
                "question": "Master, I require clarification on the intended task.",
            },
        })

    tier, score = orch.classify_tier(task_text)
    agents = orch.scan_keywords(task_text)

    if not agents:
        return json.dumps({
            "tool": "add_to_kb",
            "params": {
                "todo_id": "unknown",
                "content": task_text,
                "category": "preference",
            },
        })

    agent = agents[0]
    tool_map = {
        "meeting_agent": {
            "tool": "schedule_event",
            "params": {
                "todo_id": "unknown",
                "attendee_email": "guest@example.com",
                "start_time": "2024-01-15T10:00:00",
                "duration_minutes": 30,
                "title": f"Meeting: {task_text[:50]}",
            },
        },
        "email_agent": {
            "tool": "send_email",
            "params": {
                "todo_id": "unknown",
                "to": "recipient@example.com",
                "subject": f"Follow-up: {task_text[:40]}",
                "body": f"Master requested follow-up on: {task_text}",
            },
        },
        "knowledge_agent": {
            "tool": "add_to_kb",
            "params": {
                "todo_id": "unknown",
                "content": task_text,
                "category": "preference",
            },
        },
        "habit_agent": {
            "tool": "set_reminder",
            "params": {
                "todo_id": "unknown",
                "label": task_text[:50],
                "frequency": "daily",
                "time_of_day": "08:00",
            },
        },
    }

    action = tool_map.get(agent, tool_map["knowledge_agent"])
    return json.dumps(action)

def run_inference(model, tokenizer, todo_text=None, queue_text=None, max_steps=10):
    env = ButlerEnvironment()
    orch = Orchestrator()

    if todo_text:
        todos = [_make_todo(todo_text, orch)]
    elif queue_text:
        texts = [t.strip() for t in queue_text.split(";") if t.strip()]
        todos = [_make_todo(t, orch) for t in texts]
    else:
        print("Status: No input provided. Generating synthetic test queue.")
        todos = generate_episode_queue(min_tier1=1, min_tier2=1, total=3)

    obs = env.reset(episode_queue=todos)

    print("=" * 65)
    print("ALFRED PROTOCOL INFERENCE")
    print("=" * 65)
    print(f"\nDispatch Queue ({len(obs['queue'])} tasks):")
    for i, t in enumerate(obs["queue"], 1):
        status = "Completed" if t.get("status") == "completed" else "Pending"
        print(f"  [{status}] Tier: {t['tier']:18s} | Task {i}: {t['text']}")
    print()

    total_reward = 0.0
    violations = 0

    for step in range(1, max_steps + 1):
        if not obs.get("current_todo"):
            print("\nSuccess: All tasks in the queue have been addressed.")
            break

        current = obs["current_todo"]
        print(f"--- Step {step} ---")
        print(f"  Focus: {current['text']}")
        print(f"  Classification: {current['tier']} (Priority: {current['priority_score']})")

        prompt = (
            f"<|system|>\n{SYSTEM_PROMPT}\n"
            f"<|user|>\n{build_observation_prompt(obs)}\n"
            f"<|assistant|>\n"
        )
        raw_output = generate_action(model, tokenizer, prompt)

        action = parse_llm_output(raw_output)
        if action is None:
            print(f"  Alert: Parse failed for output: {raw_output[:80]}")
            action = {"tool": "ask_clarification", "params": {"todo_id": current.get("todo_id", ""), "field": "logic", "question": "Alfred logic error."}}

        if "params" in action and not action["params"].get("todo_id"):
            action["params"]["todo_id"] = current.get("todo_id", "")

        valid, error = validate_action(action)
        if not valid:
            print(f"  Warning: Invalid Action - {error}")

        print(f"  Action: {action['tool']} | Parameters: {json.dumps(action.get('params', {}), indent=None)[:80]}")

        obs, reward, done, info = env.step(action)
        total_reward += reward

        if info.get("priority_violation"):
            violations += 1
            print("  ALERT: PRIORITY VIOLATION DETECTED (-0.3 Penalty Applied)")

        print(f"  Step Reward: {reward:.3f} | Total: {total_reward:.3f}")

        if done:
            break

    completed = sum(1 for t in env.todo_queue if t.get("status") == "completed")
    total = len(env.todo_queue)

    print("\n" + "=" * 65)
    print("EPISODE SUMMARY REPORT")
    print("=" * 65)
    print(f"  Final Reward Score:     {total_reward:.3f}")
    print(f"  Priority Violations:    {violations}")
    print(f"  Completion Rate:        {completed}/{total} tasks")
    print(f"  Orchestration Steps:    {env.step_count}")
    print("=" * 65)

    return total_reward, violations, completed, total

def _make_todo(text: str, orch: Orchestrator) -> dict:
    import uuid
    from datetime import datetime, timezone

    tier, score = orch.classify_tier(text)
    return {
        "todo_id": uuid.uuid4().hex[:12],
        "text": text,
        "tier": tier,
        "priority_score": score,
        "expected_agent": orch.get_expected_agent(text),
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }

def compare_baseline_vs_trained(trained_model_name: str, n_episodes: int = 10):
    print(f"Status: Initiating Comparative Analysis for {trained_model_name}")
    model, tokenizer = load_model(trained_model_name)

    baseline_rewards, trained_rewards = [], []
    baseline_violations, trained_violations = [], []

    for ep in range(n_episodes):
        queue = generate_episode_queue(min_tier1=1, min_tier2=1, total=3)

        b_reward, b_viol = _run_baseline_episode(queue)
        baseline_rewards.append(b_reward)
        baseline_violations.append(b_viol)

        env = ButlerEnvironment()
        obs = env.reset(episode_queue=[t.copy() for t in queue])
        t_reward, t_viol = 0.0, 0

        for _ in range(env.MAX_STEPS_PER_EPISODE):
            if not obs.get("current_todo"): break
            prompt = f"<|system|>\n{SYSTEM_PROMPT}\n<|user|>\n{build_observation_prompt(obs)}\n<|assistant|>\n"
            raw = generate_action(model, tokenizer, prompt)
            action = parse_llm_output(raw) or {"tool": "ask_clarification", "params": {"todo_id": obs["current_todo"].get("todo_id", ""), "field": "fail", "question": "Error"}}
            
            if "params" in action and not action["params"].get("todo_id"):
                action["params"]["todo_id"] = obs["current_todo"].get("todo_id", "")

            obs, reward, done, info = env.step(action)
            t_reward += reward
            if info.get("priority_violation"): t_viol += 1
            if done: break

        trained_rewards.append(t_reward)
        trained_violations.append(t_viol)

    print("\n" + "=" * 90)
    print("ALFRED SYSTEM COMPARISON: BASELINE vs TRAINED")
    print("=" * 90)
    print(f"{'Episode':>8} | {'Base Reward':>15} | {'Alfred Reward':>15} | {'Base Violations':>15} | {'Alfred Violations':>15}")
    print("-" * 90)

    for i in range(n_episodes):
        print(f"{i+1:>8} | {baseline_rewards[i]:>15.3f} | {trained_rewards[i]:>15.3f} | {baseline_violations[i]:>15} | {trained_violations[i]:>15}")

    print("-" * 90)
    avg = lambda x: sum(x) / n_episodes
    print(f"{'Average':>8} | {avg(baseline_rewards):>15.3f} | {avg(trained_rewards):>15.3f} | {avg(baseline_violations):>15.1f} | {avg(trained_violations):>15.1f}")
    print("=" * 90)

def _run_baseline_episode(queue: list[dict]) -> tuple[float, int]:
    env = ButlerEnvironment()
    obs = env.reset(episode_queue=[t.copy() for t in queue])
    total_reward, violations = 0.0, 0
    tools = ["schedule_event", "send_email", "set_reminder", "add_to_kb"]

    for _ in range(env.MAX_STEPS_PER_EPISODE):
        if not obs.get("current_todo"): break
        current = obs["current_todo"]
        tool = random.choice(tools)
        todo_id = current.get("todo_id", "")

        action = {"tool": tool, "params": {"todo_id": todo_id}}
        if tool == "schedule_event":
            action["params"].update({"attendee_email": "test@test.com", "start_time": "2024-01-15T10:00:00", "duration_minutes": 30, "title": "Random"})
        elif tool == "send_email":
            action["params"].update({"to": "test@test.com", "subject": "Random", "body": "Random"})
        elif tool == "set_reminder":
            action["params"].update({"label": "Random", "frequency": "daily", "time_of_day": "08:00"})
        else:
            action["params"].update({"content": "Random", "category": "preference"})

        obs, reward, done, info = env.step(action)
        total_reward += reward
        if info.get("priority_violation"): violations += 1
        if done: break

    return total_reward, violations

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Alfred System Inference Script")
    parser.add_argument("--model", required=True, help="HF model identifier")
    parser.add_argument("--todo", default=None, help="Process a single task")
    parser.add_argument("--queue", default=None, help="Process semicolon-separated tasks")
    parser.add_argument("--compare", action="store_true", help="Initiate comparison analysis")
    parser.add_argument("--n_episodes", type=int, default=10, help="Episodes for analysis")
    args = parser.parse_args()

    model, tokenizer = load_model(args.model)
    if args.compare:
        compare_baseline_vs_trained(args.model, args.n_episodes)
    else:
        run_inference(model, tokenizer, todo_text=args.todo, queue_text=args.queue)