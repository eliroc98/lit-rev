# 📚 LitRev

[![Python Version][python-badge]][python-link]
[![License: MIT][license-badge]][license-link]
[![Code style: ruff][ruff-badge]][ruff-link]

A powerful, unified search tool for academic literature reviews. Query multiple major archives like ArXiv, DBLP, and Google Scholar simultaneously through a single, intuitive interface. Available as both a command-line tool and a Streamlit web application.

---

## ✨ Key Features

-   **Unified Search**: Query multiple sources at once with a single command.
-   **Advanced Query Logic**: Uses a precise `(keywords OR...) AND (authors OR...) AND (venues OR...)` structure.
-   **Multiple Interfaces**:
    -   An interactive **Streamlit Web App** for easy, visual searching.
    -   A powerful **Command-Line Interface (CLI)** with flags for scripting and power users.
    -   An **Interactive CLI Wizard** to guide you through building a search query.

## 📡 Supported Archives

-   ACL Anthology
-   ArXiv
-   DBLP
-   Google Scholar
-   Scopus (if owning an API key)

---

## 🚀 Getting Started

### Prerequisites

-   Python 3.10+
-   [Poetry](https://python-poetry.org/docs/#installation) for dependency management.

### 1. Installation

First, clone the repository and navigate into the project directory:

```bash
git clone https://github.com/your-username/lit-rev.git
cd lit-rev
```

Next, install the required dependencies using Poetry:

```bash
poetry install
```

### 2. Configuration (API Keys)

Some of the search providers require an API key to function.

#### Scopus API Key

The Scopus search will not work without an API key from the [Elsevier Developer Portal](https://dev.elsevier.com/).

The application is configured to read the key from an environment variable named `SCOPUS_API_KEY`.

**On macOS/Linux:**
```bash
export SCOPUS_API_KEY="YOUR_KEY_HERE"
```
*(Add this line to your `.zshrc`, `.bash_profile`, or shell configuration file for it to be permanent.)*

**On Windows (Command Prompt):**
```bash
set SCOPUS_API_KEY="YOUR_KEY_HERE"
```

For local development, you can also create a `.env` file in the project root and place the key there:

```ini
# .env
SCOPUS_API_KEY="YOUR_KEY_HERE"
```

---

## 💻 Usage

You can interact with LitRev Engine in two primary ways: through the Streamlit Web App or the Command-Line Interface.

### 🌐 Streamlit Web App (Recommended)

For an easy-to-use, interactive experience, run the Streamlit application.

```bash
poetry run streamlit run app.py
```

This will start a local web server and open the application in your browser, where you can fill out the search form visually.

### ⌨️ Command-Line Interface (CLI)

The CLI is perfect for scripting, quick searches, or users who prefer the terminal.

#### Interactive Wizard

For a guided experience, run the `interactive` command:

```bash
poetry run lit-rev interactive
```
The application will prompt you for each search parameter step-by-step.

#### Direct Search with Flags

Use the `search` command with flags for precise, scripted searches.

**Basic Example: Find papers with a specific keyword.**
```bash
poetry run lit-rev search -i "large language model"
```

**Complex Example: Find papers on "mechanistic interpretability" OR "SAE" by "Neel Nanda" in "NeurIPS" or "ACL" between 2022 and 2023.**
```bash
poetry run lit-rev search \
  -i "mechanistic interpretability" \
  -i "SAE" \
  -a "Neel Nanda" \
  -v "NeurIPS" \
  -v "ACL" \
  --start-year 2022 \
  --end-year 2023
```

**Example with Macro Area (ArXiv): Find Computer Science papers on "reinforcement learning".**
```bash
poetry run lit-rev search -i "reinforcement learning" -m "Computer Science"
```

---

## 🏗️ Project Structure

The project is organized into a `lit_rev` package with a clear separation of concerns.

```
lit-rev/
├── litrev/
│   ├── __init__.py
│   ├── search/               # Each archive has its own search module
│   │   ├── acl_search.py
│   │   ├── arxiv_search.py
│   │   └── ...
│   ├── engine.py             # Core search pipeline logic
│   ├── main.py               # Typer CLI application (search, interactive)
│   ├── models.py             # Pydantic data models (SearchConfig, Paper)
│   └── utils.py              # Helper functions (logging, decorators)
├── .gitignore
├── app.py                    # The Streamlit web application entry point
├── pyproject.toml            # Poetry configuration and dependencies
└── README.md
```


## 📄 License

This project is licensed under the GNU GPLv3 License. See the [LICENSE](LICENSE) file for details.

[python-badge]: https://img.shields.io/badge/Python-3.10%2B-blue.svg
[python-link]: https://www.python.org/downloads/
[license-badge]: https://img.shields.io/badge/GNU-v3
[license-link]: https://opensource.org/licenses/gpl-3-0