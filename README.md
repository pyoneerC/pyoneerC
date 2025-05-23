<a href="https://maxcomperatore.com">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/pyoneerC/pyoneerC/main/dark_mode.svg">
    <img alt="Max Comperatore GitHub Profile README" src="https://raw.githubusercontent.com/pyoneerC/pyoneerC/main/light_mode.svg">
  </picture>
</a>

## Project Overview

This project contains the source code and assets for my dynamic GitHub profile README.
The main functionality involves a Python script (`daily.py`) that:
- Calculates my current age (uptime).
- Fetches various GitHub statistics (repositories, stars, followers, commits, contributions, PRs).
- Updates the `dark_mode.svg` and `light_mode.svg` files with this dynamic data.
- These SVGs are then displayed on my GitHub profile.

The project also includes unit tests for the Python script to ensure its core logic functions correctly.

## Setup

To set up this project locally for development or testing:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/pyoneerC/pyoneerC.git
    cd pyoneerC
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
    ```

3.  **Install dependencies:**
    The project's dependencies are listed in `requirements.txt`.
    ```bash
    pip install -r requirements.txt
    ```

## Running the Daily Update

The `daily.py` script is responsible for updating the SVG files. You can run it manually from the project root:

```bash
python daily.py
```
This will update `dark_mode.svg` and `light_mode.svg` in place.

## Testing

Unit tests are located in the `tests/` directory. To run the tests, navigate to the project root and execute:

```bash
python -m unittest discover tests
```
This will automatically discover and run all tests within the `tests` directory.
