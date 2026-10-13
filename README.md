# Spotify AI Engine

## Student Onboarding

This project is a small natural-language analytics app for Spotify track metadata and audio features. Ask a question in the Streamlit interface; a language model proposes SQL, the app validates that SQL, and DuckDB runs it against the local catalog. Results appear as a table and, when appropriate, a chart.

## Workshop primer

### From app records to analysis

An app might record a playlist save, a purchase, or a track play. Systems that handle these individual transactions are often called OLTP databases, for online transaction processing. Data engineering prepares collected records for questions: it cleans them, defines what each field means, and stores them in a form that can be analyzed. OLAP, or online analytical processing, describes work such as joining and summarizing many records.

This project starts with a Spotify dataset and prepares it for analysis. DuckDB runs the SQL. The language model helps translate a student's question into SQL, while the database calculates the result from the stored rows.

### Why collect and analyze data?

A dataset gives us records we can inspect and compare. Queries can answer questions such as which tracks are most popular or how energy changes across tempo ranges. A language model can help express those questions in SQL, but its output still needs review: the generated query should match the question, and the returned rows should support the conclusion.

### Start with the grain

The grain is what one row represents. Knowing it helps you choose the right joins and avoid counting the same thing more than once.

| File | One row represents |
| --- | --- |
| `tracks.parquet` | One unique Spotify track ID and its metadata |
| `audio_features.parquet` | The audio-feature measurements for a track ID |

The preparation script removes duplicate `track_id` values before writing both files. The tables use that shared ID to connect track details with audio measurements. If a join key appears more than once when you do not expect it, a join can multiply rows and distort counts or averages.

### Practices in this project

- Keep data at track level so later queries can group it in different ways.
- Store the Parquet files separately from the DuckDB engine that queries them.
- Make preparation repeatable. The script drops incomplete rows, deduplicates by `track_id`, and writes the output files instead of appending another copy each time.
- Give fields clear meanings and units. For example, `tempo` is measured in beats per minute, `popularity` ranges from 0 to 100, and audio-feature scores have defined numeric scales.

To begin the lab, look at `scripts/step_1_prepare_data.py` and find where it cleans the source data and splits it into two files. Then read `src/prompts.py` to see how the model learns the schema and field meanings. When you use the app, compare the generated SQL with your question before interpreting the results.

## Quick Start

### Requirements

- Python 3.13 or newer
- [uv](https://docs.astral.sh/uv/)
- An API key for your selected model provider, or a running local OpenAI-compatible model

#### Choose a Model Provider

Set `LLM_PROVIDER` in `.env` to the provider you want to use, then configure its credential or local endpoint:

- **OpenRouter** (`LLM_PROVIDER=openrouter`): set `OPENROUTER_API_KEY`. Create an account or manage your key at [OpenRouter](https://openrouter.ai). For OpenAI-compatible model options, see the [OpenAI models documentation](https://developers.openai.com/api/docs/models); OpenRouter availability and model IDs may differ.
- **OpenAI** (`LLM_PROVIDER=openai`): set `OPENAI_API_KEY`. Browse available models in the [OpenAI models documentation](https://developers.openai.com/api/docs/models).
- **Gemini** (`LLM_PROVIDER=google`): set `GEMINI_API_KEY` or `GOOGLE_API_KEY`. Create a key in [Google AI Studio](https://aistudio.google.com/app/api-keys).
- **Ollama** (`LLM_PROVIDER=slm`): install and run a model through [Ollama](https://ollama.com/). No hosted API key is required by default; the app expects its OpenAI-compatible endpoint at `http://localhost:11434/v1`. Set `SLM_BASE_URL` if your local endpoint differs.

Run these commands in PowerShell from the project root:

```powershell
uv sync
Copy-Item .env.example .env
```

Open `.env` and configure a provider. The example selects OpenRouter by default, so set `OPENROUTER_API_KEY` to a valid key, or choose another provider above. Never commit `.env` or share API keys. See [`.env.example`](.env.example) for the supported settings.

Start the app:

```powershell
uv run streamlit run app.py
```

Streamlit prints the local URL in the terminal. Open it in a browser, ask a question, then inspect the generated SQL before reviewing the results.

The repository includes the prepared files in `data/`. If they are missing, recreate them with:

```powershell
uv run python scripts/step_1_prepare_data.py
```

This downloads the source dataset from Hugging Face, so it requires an internet connection. From the project root, you can check that the local DuckDB views work with:

```powershell
uv run python scripts/step_2_test_data.py
```

## Repository Structure

```text
.
├── app.py                         # Streamlit app and user workflow
├── pyproject.toml                 # Project metadata and dependencies
├── uv.lock                        # Locked dependency versions
├── .python-version                # Project Python version
├── .env.example                   # Model-provider configuration template
├── .streamlit/
│   └── config.toml                # App theme and display settings
├── data/
│   ├── tracks.parquet             # Track metadata table
│   └── audio_features.parquet     # Numeric audio feature table
├── docs/
│   ├── From Vibes to SQL.png      # High-level architecture illustration
│   └── STUDENT_VISUALIZATION_GUIDE.md # Prompt and chart examples
├── scripts/
│   ├── step_1_prepare_data.py     # Download, clean, and write Parquet data
│   ├── step_2_test_data.py        # Smoke-test the DuckDB data views
│   ├── test_agent.py              # Interactive agent and SQL test
│   └── test_security.py           # Check SQL validation guardrails
└── src/
	├── agent.py                   # Provider setup and Pydantic AI agent
	├── db.py                      # DuckDB connections and query execution
	├── prompts.py                 # SQL instructions and chart guidance
	└── schemas.py                 # Structured response and SQL validation
```

The app creates `logs/` when it runs. It is intentionally ignored by Git because logs can contain generated SQL and query results. Your local `.env` is also ignored.

## How the Pieces Fit

![High-level project overview showing Parquet storage, DuckDB compute, Pydantic AI orchestration, and Streamlit presentation](docs/From%20Vibes%20to%20SQL.png)

The main code hierarchy is:

1. **Interface:** `app.py` collects a question, shows progress, and presents the generated SQL and results.
2. **Prompt design:** `src/prompts.py` is a core part of the language-to-SQL behavior. It gives the model the database schema, music-vibe mappings, read-only query rules, and guidance for choosing charts.
3. **Language model:** `src/agent.py` selects Google, OpenAI, OpenRouter, or a local SLM from environment settings, then runs the agent with the prompt and structured response contract.
4. **Validation:** `src/schemas.py` validates the structured model response and rejects multiple statements, comments, and write or schema-changing SQL before execution.
5. **Data access:** `src/db.py` opens an in-memory DuckDB connection and exposes the two Parquet files as `tracks` and `audio_features` views.
6. **Presentation:** `app.py` displays query output in a table and chooses a recommended bar, line, or scatter chart when the returned columns support it.

## Technology Behind It

- **Python** connects the data preparation, agent, database, and interface code.
- **pandas** downloads and cleans the source CSV, removes incomplete rows and duplicate track IDs, then splits the records into metadata and audio-feature tables.
- **Parquet and PyArrow** store those tables as compact, column-oriented files that are efficient to scan.
- **DuckDB** runs analytical SQL directly over the local Parquet files. The app creates an in-memory connection, so no separate database server is needed.
- **Pydantic AI** connects the app to a selected language-model provider and asks for a structured response containing an explanation, SQL query, and chart recommendation.
- **Pydantic and sqlparse** validate the response and check that the query is a single read-only `SELECT` or `WITH` statement before the app executes it. The validator also rejects comments and blocked write or schema-changing keywords.
- **Streamlit** provides the browser interface, progress state, results table, and charts.
- **uv and python-dotenv** manage the Python environment and load local provider settings from `.env`.

The data files and DuckDB query execution are local. If you select a hosted model provider, the natural-language prompt and schema context are sent to that provider to generate SQL. Choose a local SLM provider if model requests must also stay on your machine.

## How a Question Becomes a Result

1. **Prepare the catalog:** `scripts/step_1_prepare_data.py` downloads the source CSV, drops incomplete records, deduplicates by `track_id`, and writes `tracks.parquet` and `audio_features.parquet`. This step is only needed if the prepared files are missing or you want to regenerate them.
2. **Load the app:** Streamlit starts `app.py`. The app reads provider settings from `.env`, initializes the agent, and opens DuckDB views over the two Parquet files.
3. **Describe the question:** You type a question or choose a student-focused prompt starter. The agent combines it with the schema and SQL instructions in `src/prompts.py`.
4. **Generate and validate SQL:** The configured model returns the structured response defined in `src/schemas.py`. The app checks the SQL before it reaches DuckDB; invalid output is shown as an error instead of being executed.
5. **Query the data:** DuckDB executes the validated statement against the local views. Track and audio-feature fields can be combined by joining on `track_id`.
6. **Explore the result:** The app displays the generated SQL, returned rows, timing, and a table or recommended chart. Provider and query details are written to local logs for troubleshooting.

## Data Model

| View | Contents | Key |
| --- | --- | --- |
| `tracks` | Track name, artists, album, popularity, and genre tag | `track_id` (primary key) |
| `audio_features` | Danceability, energy, valence, tempo, acousticness, speechiness, and instrumentalness | `track_id` (joins to `tracks.track_id`) |

Questions that combine track details and audio measurements need a join on `track_id`. Genre values such as `study`, `happy`, and `club` are dataset tags, not guarantees about how a track sounds. The agent defaults to 5 rows unless you request another count, and it must not return more than 100.

## Audio features in plain language

- **Tempo** is the speed of the beat, measured in beats per minute (BPM). At 120 BPM, a track has about 120 beats each minute. Tempo and energy describe different qualities, so a fast song can still sound gentle.
- **Energy** estimates how intense and active a track sounds. Lower values often feel calmer; higher values can feel busier or more forceful. It does not measure volume alone.
- **Valence** estimates how positive or cheerful the music sounds. Lower values tend to correspond to darker or more somber moods; higher values to brighter or happier moods.
- **Danceability** estimates how suitable a track's rhythm is for dancing, based on qualities such as beat stability and rhythmic regularity.
- **Acousticness** estimates whether a track sounds acoustic rather than electronic.

These features are useful for comparing tracks, but they are estimates and cannot fully describe how a song feels to every listener.

## Try It

Start with one of the prompt starters in the app, or ask questions such as:

- “Show the 10 most popular tracks tagged acoustic with their artists and acousticness.”
- “Compare average energy and valence across 10-BPM tempo bands.”
- “For happy-tagged tracks, compare valence with energy and include popularity.”

For more examples and guidance on interpreting audio features and charts, see the [student visualization guide](docs/STUDENT_VISUALIZATION_GUIDE.md).

## Checks and Experiments

Run the local SQL-safety checks without making a model call:

```powershell
uv run python scripts/test_security.py
```

To interactively test the configured agent outside the app:

```powershell
uv run python scripts/test_agent.py
```

This last script calls your configured provider and asks before executing generated SQL. Provider calls may use paid or rate-limited API access; check your provider's terms before experimenting.

## Dataset Credit

The Spotify track dataset used by this project is published by [maharshipandya on Hugging Face](https://huggingface.co/datasets/maharshipandya/spotify-tracks-dataset). Thank you to the dataset author for making it available for learning and experimentation. The preparation script downloads `dataset.csv` from this source. Please refer to the dataset page for its details and terms.

## Documentation Note

This README was prepared with AI assistance from GitHub Copilot.
