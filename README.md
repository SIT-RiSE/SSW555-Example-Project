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
