# quiet-harbor-7

Financial research scripts (SEC, EDGAR, corporate finance).

Each project is a folder. Scripts run in Spyder (F5) and need no path setup:
they read from the project's `input/` folder and write to its `output/`
folder, both of which git ignores. Pulling new code never touches data.

Scripts that download from EDGAR also need `sec_user_agent.txt` at the repo
root (one line, e.g. `Name name@example.com`), created once per machine.
