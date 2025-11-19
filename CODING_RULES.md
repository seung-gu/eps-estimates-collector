# Coding Rules

## Critical Rules

1. **NEVER modify code without explicit user approval**
   - Always ask for confirmation before making changes
   - Show the plan first, then wait for approval
   - Do not make assumptions or "helpful" modifications

2. **All imports MUST be at the top of the file**
   - Never put imports inside functions
   - Use absolute paths: `from src.eps_estimates_collector.utils.csv_storage import read_csv`
   - Never use relative imports like `from ..utils import ...`

3. **Always use `uv run python` for Python commands**
   - Never use plain `python` or `python3`
   - All test commands: `uv run python -m pytest ...`
   - All compilation checks: `uv run python -m py_compile ...`

4. **Code Quality**
   - Write clean, maintainable code
   - Avoid hardcoded values
   - Follow Python 3.11+ style
   - Think before coding, don't rush

5. **Minimal Changes**
   - Only modify what is explicitly requested
   - Don't add unnecessary features
   - Don't refactor unless asked

6. **Verification**
   - Always verify code compiles after changes
   - Test if possible before claiming completion
   - Report issues immediately if found

## Import Rules

- **Always**: `from src.eps_estimates_collector.module import function`
- **Never**: `from ..module import function` (relative imports)
- **Never**: `from .module import function` (relative imports)
- **Exception**: Only in `__init__.py` files for package structure

## Command Rules

- **Python execution**: `uv run python script.py`
- **Testing**: `uv run python -m pytest ...`
- **Compilation**: `uv run python -m py_compile ...`
- **Never**: `python script.py` or `python3 script.py`

## Workflow

1. User makes a request
2. Understand the requirement clearly
3. If unclear, ask questions
4. Show the plan/approach
5. Wait for approval
6. Make minimal changes
7. Verify the changes
8. Report completion

## What NOT to Do

- ❌ Modify code without asking
- ❌ Put imports inside functions
- ❌ Use relative imports
- ❌ Use plain `python` commands
- ❌ Make unnecessary changes
- ❌ Assume what user wants
- ❌ Repeat mistakes after being told

