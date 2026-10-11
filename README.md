# Crackers portfolio — full-stack edition

This folder contains the portfolio UI, a Python JSON API, and SQLite persistence. The owner dashboard is password-protected. The public page reads published content from the server.

## Use it locally on Windows

1. Install Python 3.10 or newer.
2. Double-click `start-local.cmd` and choose a unique editor password with at least 14 characters. The launcher asks you to confirm it and generates a persistent session secret for this server run.
3. Keep the console open and visit `http://localhost:8000/` in Chrome. Sign in to edit the page.
4. The public portfolio is at `http://localhost:8000/portfolio`. Press Ctrl+C in the server window to stop it.

The local database is stored at `%LOCALAPPDATA%\PortfolioOS\portfolioos.db`. Back it up regularly. A local address works only while the server is running on your computer; it is not a public internet link.

## Publish the backend with Render

`render.yaml` defines a Python service, health check, generated session secret, and persistent SQLite disk.

1. Push the files in this folder to a Git repository.
2. Create a Render Blueprint from that repository.
3. Set `PORTFOLIO_ADMIN_PASSWORD` to a unique password of at least 14 characters. Render generates `PORTFOLIO_SESSION_SECRET` from the blueprint.
4. Deploy. The owner dashboard is at `/`; the shareable portfolio is at `/portfolio`.

SQLite needs the configured persistent disk. Confirm that your chosen Render plan supports persistent disks; Render may charge for the service or disk. Do not deploy with an ephemeral filesystem if you need portfolio data to survive restarts.

## Important: Netlify Drop and backend hosting

The active Netlify Drop URL is a static deployment. Netlify Drop serves HTML, CSS, and browser JavaScript; it does not run this Python server or its SQLite database. The backend in this folder becomes live only after deploying it to a Python host such as the Render Blueprint above. That creates a separate site URL unless you connect a custom domain.

## Owner features

- Edit profile, projects, skills, credentials, and resume sections.
- Save edits to SQLite; hide individual projects from the public page.
- Download and restore a JSON backup from the dashboard.
- Share, print, or save the public portfolio as PDF.
- Check `/api/health` for the service health response.

## Security and data notes

- Use HTTPS in production and keep both environment secrets private. Never commit passwords, session secrets, or a live database.
- Sessions use signed, HttpOnly, SameSite=Strict cookies. Only a hash of each session token is stored in SQLite; sessions survive restarts when the database and configured secret persist, and expire after seven days.
- The editor has same-origin mutation checks, request-size limits, URL and email validation, security response headers, and a short in-memory login rate limit. The rate limit resets if the process restarts and is not shared across multiple service instances; this project is intended for a single-owner, single-instance portfolio.
- The public page displays profile content and any populated resume fields. Only enter information you intend to publish.
- SQLite is suitable for this low-volume single-owner app. Multi-user accounts, contact-message collection, uploads, and horizontally scaled services need additional infrastructure and are not included.
