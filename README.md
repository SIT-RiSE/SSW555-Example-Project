# Routine Rebels

[![CI](https://github.com/agupta5555/SSW555-Routine-Rebels/actions/workflows/ci.yml/badge.svg)](https://github.com/agupta5555/SSW555-Routine-Rebels/actions/workflows/ci.yml)

Routine Rebels is a daily routine tracker that helps people record habits,
monitor their progress, and build consistent routines.

## Team

- Aryan Gupta
- Nikunj Patel
- Neil Motiani
- Aarnav Hariramani

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

## Today's habits (US-12)

Choose **Today** on the Habit Tracker (`/habit-tracker?view=today`) to see
habits scheduled for the server's current weekday. Habits without a weekday
schedule remain available every day. Frequency defines the progress/streak
period independently of the weekday schedule. The view recalculates on each
request, including after schedule changes or day rollover. **All habits**
returns to the full list for managing schedules; the default view stays the
full list.
