from getpass import getpass
from pathlib import Path
import os
import runpy
import secrets

password = getpass('Choose an editor password (at least 14 characters): ')
if len(password) < 14:
    raise SystemExit('Password is too short. Close this window and launch again with 14 or more characters.')
confirm = getpass('Confirm password: ')
if password != confirm:
    raise SystemExit('Passwords did not match. Close this window and launch again.')

local_data = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'PortfolioOS'
local_data.mkdir(parents=True, exist_ok=True)
os.environ['PORTFOLIO_ADMIN_PASSWORD'] = password
os.environ['PORTFOLIO_SESSION_SECRET'] = secrets.token_urlsafe(48)
os.environ['DATABASE_PATH'] = str(local_data / 'portfolioos.db')
os.environ['PORT'] = '8000'
print('\nStarting PortfolioOS. Keep this window open.')
print('Owner dashboard: http://localhost:8000/')
print('Public portfolio: http://localhost:8000/portfolio')
print('Press Ctrl+C here to stop the server.\n', flush=True)
runpy.run_path(str(Path(__file__).with_name('server.py')), run_name='__main__')
