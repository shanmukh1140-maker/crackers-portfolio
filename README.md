# Crackers — Student Portfolio

Crackers includes the live static portfolio and a separate full-stack portfolio app.

## Live website

The public website is deployed at [heartfelt-blini-a80288.netlify.app](https://heartfelt-blini-a80288.netlify.app/). Its source is `portfolioos-student-portfolio.html`. It is a self-contained HTML app with responsive layouts, a searchable command palette (Ctrl+K), a saved light/dark theme, project and profile editors, and browser-local storage.

To deploy that standalone page through Netlify Drop, upload the HTML file. It runs as a static site and stores edits in the visitor's browser; it does not use the Python backend below.

## Full-stack app

The root `index.html` and `server.py` make up the separate full-stack version. It provides a Python JSON API and SQLite persistence, with an owner dashboard and public portfolio route.

### Run on Windows

1. Install Python 3.10 or newer.
2. Double-click `start-local.cmd` and choose a unique editor password with at least 14 characters.
3. Keep the server window open and visit `http://localhost:8000/` in Chrome. The public portfolio route is `/portfolio`.
4. Press Ctrl+C in the server window to stop it.

The local database is stored at `%LOCALAPPDATA%\PortfolioOS\portfolioos.db`. A localhost address works only while the server is running on your computer.

### Publish the backend with Render

`render.yaml` defines a Python service, health check, generated session secret, and persistent SQLite disk.

1. Deploy this repository as a Render Blueprint.
2. Set `PORTFOLIO_ADMIN_PASSWORD` to a unique password of at least 14 characters.
3. Confirm the selected plan supports persistent disks and deploy.

The backend deployment gets its own service URL unless you connect a custom domain. Netlify Drop does not run the Python API or SQLite database.

## Security and data

- Keep passwords, session secrets, and database files private; do not commit them.
- Production use requires HTTPS. Session tokens are stored as hashes in SQLite and expire after seven days.
- The backend validates requests and URLs and uses same-origin mutation checks and security headers. It is designed for a single owner and one server instance.
- Only publish personal details you want visitors to see. The standalone page stores its content in browser local storage; the full-stack app saves data on the configured backend.