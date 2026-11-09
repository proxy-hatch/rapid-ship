# Tool-settings choices

Leave purely stylistic differences out of the tool-settings PR. For Ruff these are `line-length`, `indent-width`, `[tool.ruff.format]` and its `quote-style`, `indent-style`, `line-ending`, `skip-magic-trailing-comma`, `docstring-code-format` and `docstring-code-line-length` options, and the `E501`, `Q` and `COM` rules that only enforce them. For Prettier, leave out every option. For ESLint, leave out `@stylistic/*` and core formatting rules that Prettier replaces. Mypy, pytest, import-linter, `tsconfig.json`, Vitest and knip have no stylistic options to exclude here.

Offer the rules behind doctor's floor items, with what each catches. Also offer Ruff `ASYNC` when the project imports asyncio and `FAST` when it imports FastAPI. The owner picks the rules.
