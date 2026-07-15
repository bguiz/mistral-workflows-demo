# Mutimodel Joke

[Mistral Workflows](https://docs.mistral.ai/workflows/getting-started/introduction)
demonstrating multi-modal use of Mistral AI models.

## Setup

```bash
uv sync
cp .env.example .env
```

Fill in `MISTRAL_API_KEY`, `DEPLOYMENT_NAME`, and `CLOUDINARY_` values.

Note that Cloudinary is needed to host generated audio.
Visit [`console.cloudinary.com`](https://console.cloudinary.com/),
go to "quick start", and click on "view API keys" to obtain credentials.

## Commands

### Register workflows with Mistral AI Studio

Auto-discovers all workflow classes in `src/workflows/`, registers them with AI Studio, and starts polling for executions. The [deployment name](https://docs.mistral.ai/workflows/managing-workflows-in-production/deployments) is set to `{hostname}-{project}-{adjective}-{noun}` so multiple projects on the same machine stay isolated:

```bash
make start-worker
```

### Execute a workflow

#### CLI

In a separate terminal, trigger a workflow execution by name:

```bash
make execute workflow=multimodal-joke input='{"name": "Martín Alvarez Bellini", "lanaguage": "es-AR"}'
```

#### Mistral Studio

1. Navigate to [console.mistral.ai](https://console.mistral.ai/)
1. In the left nav menu, select "workflows", then "list"
1. Select "Multimodal Joke Demo"
1. Press "start workflow" button (top right)
   - If button is greyed out, restart the worker (`make start-worker`), then refresh this page
1. Fill in the input JSON object
   - For example: `{"name": "Martín Alvarez Bellini", "lanaguage": "es-AR"}`
1. Press "start workflow" button (bottom right)
1. Observe the Gantt Chart showing each activity executing
1. Select each activity from the bottom left to view its inputs and outputs

## Project layout

```
src/
├── entrypoints/ # Runnable modules, invoked via `python -m entrypoints.<module>`
│   ├── worker.py   # `python -m entrypoints.worker` - discover and run workflows
│   ├── start.py    # `python -m entrypoints.start`  - trigger a workflow execution
│   └── dev.py      # `python -m entrypoints.dev`    - worker with file-watch auto-reload
├── workflows/   # Your workflow classes (auto-discovered by `entrypoints.worker`)
│   ├── activities.py   # Each "task" within the workflow
│   ├── models.py       # Pydantic datatype definitions used to interface between activities and workflow
│   └── workflow.py     # Defines the sequences of the workflows to execute
```

## Development

```bash
# Format
uv run ruff format .

# Lint
uv run ruff check --fix .
```
