"""Interactively test the configured Pydantic AI SQL agent."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.db import execute_query, get_db_connection
from src.agent import sql_agent
from src.schemas import SQLQueryResponse


def execute_generated_sql(response: SQLQueryResponse):
    """Execute validated generated SQL and close the in-memory connection."""
    connection = get_db_connection()
    try:
        return execute_query(connection, response.sql_query)
    finally:
        connection.close()


def main() -> None:
    user_prompt = input("Enter a natural-language question about the Spotify data: ").strip()
    if not user_prompt:
        raise SystemExit("Please enter a question to test the agent.")

    result = sql_agent.run_sync(user_prompt)
    response = result.output

    print(f"\nInterpretation: {response.thought_process}")
    print(f"\nGenerated SQL:\n{response.sql_query}")
    print(f"\nChart recommendation: {response.chart_recommendation}")

    confirmation = input("\nExecute this SQL? [y/N]: ").strip().lower()
    if confirmation != "y":
        print("Execution skipped.")
        return

    results = execute_generated_sql(response)
    print("\nQuery results:")
    print(results.to_string(index=False) if not results.empty else "No rows returned.")


if __name__ == "__main__":
    main()