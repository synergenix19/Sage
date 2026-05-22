# Backlog: Multi-Turn Signal Enforcement in step_policy

**ID:** GATE-6
**Type:** Schema + runtime enhancement
**Priority:** Low (no current runtime failure)
**Blocks:** Nothing in current sprints

---

## Problem

All `resistance > 6` and `engagement < 3` step_policy rules include `"turns": 3` in the condition object, meaning "this condition must persist for 3 consecutive turns before the rule fires." This is the clinically correct behavior — a user who is briefly disengaged should not trigger a skill switch; only sustained disengagement should.

The `turns` field is currently silently ignored. `StepPolicyCondition` in `schema.py` has no `turns` attribute. `evaluate_step_policy` in `skill_executor.py` checks the condition on a single turn only.

This means the rules fire on the first matching turn rather than after 3 consecutive turns as authored.

**Concrete impact:** A user who gives a short answer to one step but re-engages the next turn would incorrectly trigger `offer_skill_switch_or_break` or `check_in_micro` on that single short answer.

---

## Spec

### Schema change

Add `turns: int | None = None` to `StepPolicyCondition` in `schema.py`:

```python
class StepPolicyCondition(BaseModel):
    signal: str
    operator: str
    value: Any
    step: str
    turns: int | None = None  # add this
```

### State change

`SageState` needs a `step_policy_signal_history` field:

```python
step_policy_signal_history: dict[str, list[float | bool]] = {}
```

This dict maps signal names to a rolling list of recent values (capped at `max(turns)` length across all rules, or a fixed window like 5).

### Executor change

In `evaluate_step_policy`, when a condition has `turns: N`:
1. Append the current signal value to `step_policy_signal_history[signal]`
2. Only fire if the last N values in the history all satisfy the condition
3. Reset the history for that signal when any rule fires

```python
if cond.turns is not None:
    history = state.step_policy_signal_history.setdefault(cond.signal, [])
    history.append(signal_value)
    if len(history) > cond.turns:
        history.pop(0)
    if len(history) < cond.turns:
        continue  # not enough history yet
    if not all(op_fn(v, cond.value) for v in history):
        continue  # condition not sustained
```

### Test spec

1. `test_resistance_single_turn_does_not_fire`: resistance=7 for 1 turn → action is `advance` not `offer_skill_switch_or_break`
2. `test_resistance_two_turns_does_not_fire`: resistance=7 for 2 turns → action is `advance`
3. `test_resistance_three_turns_fires`: resistance=7 for 3 turns → action is `offer_skill_switch_or_break`
4. `test_resistance_resets_after_fire`: resistance=7 for 3 turns fires, then resistance drops, then resistance=7 for 1 turn → no fire (history reset)
5. Same 4 tests for `engagement < 3`

---

## Dependencies

- `SageState` must be passed into `evaluate_step_policy` (currently only `skill` object is passed)
- The state dict passed to `evaluate_step_policy` likely needs a new parameter: `signal_history: dict`
- Or the executor node manages history directly in SageState and passes it in

## Estimated effort

2-3 hours: schema change + state field + executor logic + 10 tests. No LLM changes required.

## When to implement

After the FPE and cultural review gates (Gates 1 and 2) are cleared. The current behavior (fires on first matching turn) is overly sensitive but not dangerous. It may cause slightly premature skill switches, but it does not suppress crisis detection or violate safety invariants.
