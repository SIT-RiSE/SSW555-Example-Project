# Routine Rebels

[![CI](https://github.com/agupta5555/SSW555-Routine-Rebels/actions/workflows/ci.yml/badge.svg)](https://github.com/agupta5555/SSW555-Routine-Rebels/actions/workflows/ci.yml)

Routine Rebels is a daily routine tracker that helps people record habits,
monitor their progress, and build consistent routines.

## Team

- Aryan Gupta
- Nikunj Patel
- Neil Motiani
- Aarnav Hariramani

## Record a habit completion (US-08)

On the Habit Tracker, choose **Mark complete** for a habit due today. The
completion is saved for the server's current date and the card shows
**Completed today** after reloading. Existing completion history is preserved.
Habits with selected weekdays can only be completed on those days; habits
without a weekday schedule are available every day. Frequency continues to
define the progress/streak period independently of the weekday schedule.

## Local development

```bash
uv sync --extra dev
uv run flask --app app run --debug
```

Run the same checks used by CI:

```bash
uv run ruff check .
uv run pytest -v
```

## Daily completions

Use **Mark complete** beside a habit to record today's completion. The button
shows **Completed today** afterward. Repeated submissions record the date only
once; simultaneous submissions preserve existing history. Completion dates use
the server's local calendar day and are stored as a JSON list in `completed_dates`.

US-09 regression tests: `uv run pytest tests/test_us09_duplicate_completions.py`.

## Today's habits (US-12)

Choose **Today** on the Habit Tracker (`/habit-tracker?view=today`) to see
habits scheduled for the server's current weekday. Habits without a weekday
schedule remain available every day. Frequency defines the progress/streak
period independently of the weekday schedule. The view recalculates on each
request, including after schedule changes or day rollover. **All habits**
returns to the full list for managing schedules; the default view stays the
full list.
