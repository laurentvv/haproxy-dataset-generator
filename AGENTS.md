# AGENTS.md

## Setup commands

- **Install dependencies** (using uv - recommended for Python projects):
  ```bash
  uv sync
  ```

- **Start dev server** (Gradio app):
  ```bash
  uv run python 04_chatbot.py
  ```

- **Run tests**:
  ```bash
  uv run pytest
  ```

- **Format code** (mandatory after any modification):
  ```bash
  uv run ruff check --fix .
  uv run ruff format .
  ```

## Code style

- **Python version**: 3.13
- **PEP 8 compliance**: Follow Python's official style guide
- **Type hints**: Use strict type annotations with `typing` module
- **Docstrings**: Follow Google or NumPy docstring conventions
- **Import ordering**: Use `ruff` for automatic import sorting
- **Line length**: Maximum 100 characters (configurable in ruff)
- **String quotes**: Use double quotes for docstrings, single quotes for code strings
- **Whitespace**: No trailing whitespace, use 4 spaces for indentation

## Framework specifics (Gradio 6.6.0)

This project uses **Gradio 6.6.0** for building interactive web UIs.

### Core Gradio patterns

**Interface (high-level)**:
```python
import gradio as gr

def greet(name: str) -> str:
    return f"Hello {name}!"

gr.Interface(fn=greet, inputs="text", outputs="text").launch()
```

**Blocks (low-level)**:
```python
import gradio as gr

with gr.Blocks() as demo:
    name = gr.Textbox(label="Name")
    output = gr.Textbox(label="Greeting")
    btn = gr.Button("Greet")
    btn.click(fn=lambda n: f"Hello {n}!", inputs=name, outputs=output)

demo.launch()
```

**ChatInterface** (for chatbots):
```python
import gradio as gr

def respond(message: str, history: list[tuple[str, str]]) -> str:
    return f"You said: {message}"

gr.ChatInterface(fn=respond).launch()
```

### Key components

- `Textbox`: Text input/output with optional multi-line support
- `Chatbot`: Display chat history with user and assistant messages
- `Button`: Trigger events with `.click()` method
- `Markdown`: Render formatted text
- `State`: Manage session state across interactions

### Event listeners

All components support event listeners with this signature:
```python
component.event_name(
    fn: Callable,
    inputs: Component | Sequence[Component] | None = None,
    outputs: Component | Sequence[Component] | None = None,
    api_name: str | None = None,
    show_progress: Literal["full", "minimal", "hidden"] = "full",
    queue: bool = True,
    # ... additional parameters
)
```

Common events:
- `Button.click()`: Handle button clicks
- `Textbox.change()`, `Textbox.input()`: React to text changes
- `Chatbot.change()`: Monitor chat history updates

## Development workflow

1. **Make changes** to Python files
2. **Format code** with ruff (mandatory):
   ```bash
   uv run ruff check --fix .
   uv run ruff format .
   ```
3. **Test changes** locally by running the Gradio app
4. **Commit** only after ruff passes without errors

## Linting configuration

The project uses **ruff** (>=0.15.2) for linting and formatting. Configuration is in `pyproject.toml` under `[tool.ruff]`.

Key rules enforced:
- E, F, W: Error, flake8, and warning rules
- I: Import sorting
- UP: Upgrade syntax to modern Python
- B: Bugbear (common pitfalls)
- C4: Comprehensions optimization

Run `uv run ruff check .` to see all linting rules in effect.
