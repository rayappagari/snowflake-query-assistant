import argparse
import sys

from dotenv import load_dotenv

# Load .env before any agent modules are imported — Anthropic and Snowflake
# clients initialize at import time and read credentials from the environment.
load_dotenv()

from agents.orchestrator import answer_question


def main() -> None:
    parser = argparse.ArgumentParser(description="Snowflake multi-agent query assistant")
    parser.add_argument(
        "--query", "-q",
        help="Run a single question and exit (non-interactive mode)",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress agent step logs",
    )
    args = parser.parse_args()

    verbose = not args.quiet

    if args.query:
        print(answer_question(args.query, verbose=verbose))
        return

    print("Snowflake Query Assistant — type your question or 'exit' to quit.\n")
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            sys.exit(0)

        if not question:
            continue
        if question.lower() in ("exit", "quit", "bye"):
            print("Goodbye!")
            break

        answer = answer_question(question, verbose=verbose)
        print(f"\nAssistant: {answer}\n")


if __name__ == "__main__":
    main()
