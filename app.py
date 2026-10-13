"""
app.py
Streamlit UI for the DIY Spotify Wrapped AI Data Engine.
Stack: DuckDB (OLAP) + Pydantic AI (Validation/Text-to-SQL) + Streamlit (UI)
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import time
from urllib.parse import urlparse
import streamlit as st
from pydantic_ai.messages import ModelResponse

from src.db import get_db_connection, execute_query
from src.agent import sql_agent

logger = logging.getLogger("spotify_ai_engine")
logger.setLevel(logging.INFO)
logger.propagate = False
log_dir = Path(__file__).resolve().parent / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

if not any(handler.get_name() == "spotify_ai_engine_console" for handler in logger.handlers):
    console_handler = logging.StreamHandler()
    console_handler.set_name("spotify_ai_engine_console")
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)

if not any(handler.get_name() == "spotify_ai_engine_file" for handler in logger.handlers):
    file_handler = RotatingFileHandler(
        log_dir / "spotify_ai_engine.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.set_name("spotify_ai_engine_file")
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)


def get_model_sources(agent_result) -> str:
    """Return distinct provider/model pairs used during this agent run."""
    model_sources = []
    for message in agent_result.all_messages():
        if not isinstance(message, ModelResponse):
            continue

        provider = message.provider_name or "unknown"
        hostname = urlparse(message.provider_url or "").hostname or ""
        if hostname.endswith("openrouter.ai"):
            provider = "openrouter"
        elif hostname in {"localhost", "127.0.0.1", "::1"}:
            provider = "slm"

        model_source = f"provider={provider}, model={message.model_name or 'unknown'}"
        if model_source not in model_sources:
            model_sources.append(model_source)

    return ", ".join(model_sources) or "unknown"

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Spotify listening lab",
    page_icon=":material/graphic_eq:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Listening lab", icon=":material/graphic_eq:")
st.caption("Spotify track metadata and measured audio features")

# ---------------------------------------------------------------------------
# Initialize Session State
# ---------------------------------------------------------------------------
st.session_state.setdefault("user_query", "")
st.session_state.setdefault("agent_running", False)
st.session_state.setdefault("analysis_pending", False)
st.session_state.setdefault("analysis_result", None)
st.session_state.setdefault("analysis_error", None)


def queue_analysis(prompt_text: str | None = None) -> None:
    """Queue one analysis and disable controls before Streamlit reruns."""
    if st.session_state.agent_running:
        return
    if prompt_text is not None:
        st.session_state.user_query = prompt_text
    if not st.session_state.user_query.strip():
        return

    st.session_state.agent_running = True
    st.session_state.analysis_pending = True
    st.session_state.analysis_result = None
    st.session_state.analysis_error = None


# ---------------------------------------------------------------------------
# Database initialization
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="Loading track catalog...")
def init_db():
    return get_db_connection()


try:
    con = init_db()
except Exception as error:
    st.error(f"Could not load the database views: {error}")
    st.info("Generate the Parquet files with `uv run python scripts/prepare_data.py`.")
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar: catalog and safeguards
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Catalog", icon=":material/database:")
    try:
        counts_df = con.sql(
            """
            SELECT
                (SELECT COUNT(*) FROM tracks) AS tracks_count,
                (SELECT COUNT(*) FROM audio_features) AS features_count;
            """
        ).df()
        st.metric("Tracks", f"{counts_df['tracks_count'][0]:,}")
        st.metric("Audio feature rows", f"{counts_df['features_count'][0]:,}")
    except Exception:
        st.warning("Parquet views are not initialized.")

    st.subheader("Read-only safeguards", icon=":material/shield:")
    st.markdown(
        "- `sqlparse` statement validation\n"
        "- Single statement only\n"
        "- DDL/DML keywords blocked\n"
        "- In-memory DuckDB views"
    )
    st.caption("DuckDB · Parquet · Pydantic AI")

# ---------------------------------------------------------------------------
# Question and prompt starters
# ---------------------------------------------------------------------------
st.subheader("Ask the catalog", icon=":material/search:")
agent_running = st.session_state.agent_running
query_col, run_col = st.columns([5, 1], vertical_alignment="bottom")
with query_col:
    query_input = st.text_input(
        "Natural-language question",
        key="user_query",
        placeholder="Compare energy and valence across tempo bands",
        disabled=agent_running,
    )
run_col.button(
    "Run",
    type="primary",
    icon=":material/play_arrow:",
    help="Generate SQL, validate it, and run it against the catalog.",
    width="stretch",
    disabled=agent_running,
    on_click=queue_analysis,
)

st.subheader("Prompt starters", icon=":material/graphic_eq:")
c1, c2, c3, c4 = st.columns(4, gap="small")

c1.button(
    "Focus before class",
    icon=":material/music_note:",
    width="stretch",
    help="Build a calm study queue for the time before class.",
    disabled=agent_running,
    on_click=queue_analysis,
    args=("I'm settling in to study before class. Find 10 tracks tagged study with energy below 0.45 and acousticness above 0.5. Show track_name, artists, energy, acousticness, and popularity.",),
)
c2.button(
    "Walk between classes",
    icon=":material/menu_book:",
    width="stretch",
    help="Find upbeat tracks for the walk to your next class.",
    disabled=agent_running,
    on_click=queue_analysis,
    args=("I'm walking between classes and want upbeat music. Find 10 tracks tagged happy with valence above 0.65 and tempo above 110 BPM. Show track_name, artists, valence, tempo, and popularity.",),
)
c3.button(
    "Quick gym break",
    icon=":material/wb_sunny:",
    width="stretch",
    help="Pick high-energy tracks for a short workout between classes.",
    disabled=agent_running,
    on_click=queue_analysis,
    args=("I have a quick workout between classes. Find 10 tracks tagged club with danceability above 0.7 and energy above 0.75, ordered by popularity. Show track_name, artists, danceability, energy, and popularity.",),
)
c4.button(
    "Wind down tonight",
    icon=":material/graphic_eq:",
    width="stretch",
    help="Find mellow instrumental tracks to unwind after a long day.",
    disabled=agent_running,
    on_click=queue_analysis,
    args=("I'm winding down after a long day. Find 10 tracks tagged lofi with instrumentalness above 0.5 and energy below 0.45. Show track_name, artists, instrumentalness, energy, and popularity.",),
)

# ---------------------------------------------------------------------------
# Queued analysis
# ---------------------------------------------------------------------------
if st.session_state.analysis_pending:
    st.session_state.analysis_pending = False
    user_prompt = st.session_state.user_query.strip()
    with st.spinner("Generating SQL and querying the catalog..."):
        stage = "agent"
        stage_start_time = time.perf_counter()
        try:
            agent_result = sql_agent.run_sync(user_prompt)
            agent_elapsed_ms = (time.perf_counter() - stage_start_time) * 1000
            data = agent_result.output
            usage = agent_result.usage
            logger.info(
                "LLM %s; completed in %.2f ms; requests=%d, "
                "input_tokens=%d, output_tokens=%d, total_tokens=%d",
                get_model_sources(agent_result),
                agent_elapsed_ms,
                usage.requests,
                usage.input_tokens,
                usage.output_tokens,
                usage.total_tokens,
            )
            logger.info("Generated SQL:\n%s", data.sql_query)

            stage = "sql"
            stage_start_time = time.perf_counter()
            df = execute_query(con, data.sql_query)
            sql_elapsed_ms = (time.perf_counter() - stage_start_time) * 1000
            logger.info("DuckDB returned %d rows in %.2f ms", len(df), sql_elapsed_ms)
            logger.info(
                "Query results (showing at most 50 rows and 20 columns):\n%s",
                df.to_string(index=False, max_rows=50, max_cols=20),
            )
            st.session_state.analysis_result = {
                "response": data,
                "dataframe": df,
                "llm_elapsed_ms": agent_elapsed_ms,
                "sql_elapsed_ms": sql_elapsed_ms,
            }
        except Exception as err:
            error_text = str(err)
            status_code = getattr(err, "status_code", None)
            stage_elapsed_ms = (time.perf_counter() - stage_start_time) * 1000
            logger.error(
                "%s failed after %.2f ms (status/type: %s)",
                "SQL execution" if stage == "sql" else "LLM request",
                stage_elapsed_ms,
                status_code or type(err).__name__,
            )
            st.session_state.analysis_error = {
                "stage": stage,
                "status_code": status_code,
                "message": error_text,
            }
        finally:
            st.session_state.agent_running = False
    st.rerun()

if st.session_state.analysis_error is not None:
    error = st.session_state.analysis_error
    if error["stage"] == "agent" and (error["status_code"] == 429 or "429" in error["message"]):
        st.error("The selected model is rate-limited (HTTP 429).")
        st.info("Wait briefly and retry, or choose another model/provider in .env.")
    elif error["stage"] == "agent" and (
        error["status_code"] == 503 or "503" in error["message"]
    ):
        st.error("The selected LLM is temporarily unavailable (HTTP 503).")
        st.info("Wait briefly and retry, or choose another model/provider in .env.")
    elif error["stage"] == "sql":
        st.error(f"SQL execution error: {error['message']}")
    else:
        st.error(f"Agent or validation error: {error['message']}")

if st.session_state.analysis_result is not None:
    analysis = st.session_state.analysis_result
    data = analysis["response"]
    df = analysis["dataframe"]

    # Display the model interpretation and validated SQL.
    with st.expander("Generated SQL", expanded=True, icon=":material/code:"):
        st.caption(data.thought_process)
        st.code(data.sql_query, language="sql")

    metric_cols = st.columns(3)
    metric_cols[0].metric("Rows returned", f"{len(df):,}")
    metric_cols[1].metric("DuckDB time", f"{analysis['sql_elapsed_ms']:.1f} ms")
    metric_cols[2].metric("Suggested view", data.chart_recommendation.title())

    # 4. Result Presentation & Dynamic Charts
    tab_table, tab_chart = st.tabs(["Results", "Visualization"])

    with tab_table:
        st.dataframe(df, width="stretch", hide_index=True, alt="Rows returned by the generated SQL query")

    with tab_chart:
        if df.empty:
            st.info("No data returned for this query.")
        elif data.chart_recommendation == "table":
            st.caption("This result is best viewed as a table.")
        elif data.chart_recommendation == "line":
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            if len(numeric_cols) >= 2:
                x_col = numeric_cols[0]
                y_cols = numeric_cols[1:]
                st.line_chart(
                    df,
                    x=x_col,
                    y=y_cols,
                    alt=f"{', '.join(y_cols)} by {x_col}",
                )
            else:
                st.info("A line chart needs an ordered numeric x-axis and at least one numeric series.")
        elif data.chart_recommendation == "scatter":
            if {"energy", "valence"}.issubset(df.columns):
                size_col = "popularity" if "popularity" in df.columns else None
                st.scatter_chart(
                    df,
                    x="valence",
                    y="energy",
                    size=size_col,
                    alt="Track energy compared with musical positivity; popularity sets marker size when available",
                )
            else:
                st.info("A scatter plot needs both energy and valence columns.")
        elif data.chart_recommendation == "bar":
            if {"track_name", "popularity"}.issubset(df.columns):
                chart_df = df.set_index("track_name")[["popularity"]].sort_values("popularity", ascending=False)
                st.bar_chart(chart_df, alt="Track popularity, highest first")
            else:
                numeric_cols = df.select_dtypes(include="number").columns
                if len(numeric_cols) > 0:
                    text_cols = df.select_dtypes(include="object").columns
                    if len(text_cols) > 0:
                        st.bar_chart(
                            df.set_index(text_cols[0])[numeric_cols[0]],
                            alt=f"{numeric_cols[0]} by {text_cols[0]}",
                        )
                    else:
                        st.bar_chart(df[numeric_cols], alt="Numeric measures returned by the query")
                else:
                    st.info("A bar chart needs at least one numeric measure.")
        else:
            st.caption("No chart was recommended for this result.")