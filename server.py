from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get('DATABASE_PATH', str(ROOT / 'portfolioos.db')))
PORT = int(os.environ.get('PORT', '8000'))
ADMIN_PASSWORD = os.environ.get('PORTFOLIO_ADMIN_PASSWORD', '')
SESSION_SECRET = os.environ.get('PORTFOLIO_SESSION_SECRET') or secrets.token_urlsafe(48)
MAX_BODY = 1_000_000
ATTEMPTS: dict[str, list[float]] = {}
SESSION_TTL = 60 * 60 * 24 * 7

STARTER = {
    'profile': {
        'name': 'Your Name', 'headline': 'Student · Aspiring Software Developer',
        'location': 'Your City', 'email': '', 'website': '', 'github': '', 'linkedin': '',
        'about': 'Write a short introduction about what you are learning, building, and hoping to do next.'
    },
    'projects': [], 'skills': [], 'certificates': [],
    'resume': {'summary': '', 'experience': '', 'achievements': ''}
}


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=15)
    return db


def init_db() -> None:
    with connect() as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('CREATE TABLE IF NOT EXISTS portfolio (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
        db.execute('CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, created_at INTEGER NOT NULL, last_seen_at INTEGER NOT NULL, expires_at INTEGER NOT NULL)')
        db.execute('CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires_at)')
        db.execute('DELETE FROM sessions WHERE expires_at <= ?', (int(time.time()),))
        if db.execute('SELECT 1 FROM portfolio WHERE id=1').fetchone() is None:
            db.execute('INSERT INTO portfolio(id,data) VALUES(1,?)', (json.dumps(STARTER),))


def load_data() -> dict:
    with connect() as db:
        row = db.execute('SELECT data FROM portfolio WHERE id=1').fetchone()
    return json.loads(row[0]) if row else STARTER.copy()


def save_data(data: dict) -> None:
    with connect() as db:
        db.execute('INSERT INTO portfolio(id,data,updated_at) VALUES(1,?,CURRENT_TIMESTAMP) ON CONFLICT(id) DO UPDATE SET data=excluded.data,updated_at=CURRENT_TIMESTAMP', (json.dumps(data, ensure_ascii=False),))


def clean_text(value, limit=2000) -> str:
    return str(value or '').strip()[:limit]


def clean_url(value) -> str:
    url = clean_text(value, 500)
    if not url: return ''
    try:
        parsed = urlparse(url)
        valid_port = parsed.port is None or 1 <= parsed.port <= 65535
    except ValueError:
        valid_port = False
        parsed = None
    if not parsed or parsed.scheme not in ('http', 'https') or not parsed.hostname or not valid_port or parsed.username or parsed.password:
        raise ValueError('Links must start with https:// or http://.')
    return url


def validate_data(value) -> dict:
    if not isinstance(value, dict) or not isinstance(value.get('profile'), dict):
        raise ValueError('Portfolio data must include a profile.')
    profile = value['profile']
    data = {
        'profile': {key: clean_text(profile.get(key), 3000 if key == 'about' else 240) for key in ('name','headline','location','email','website','github','linkedin','about')},
        'projects': [], 'skills': [], 'certificates': [], 'resume': {}
    }
    for key in ('website','github','linkedin'):
        data['profile'][key] = clean_url(profile.get(key))
    if not data['profile']['name']:
        raise ValueError('Your name is required.')
    if data['profile']['email'] and not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', data['profile']['email']):
        raise ValueError('Enter a valid public email address.')
    for key in ('projects', 'skills', 'certificates'):
        if not isinstance(value.get(key, []), list):
            raise ValueError(f'{key.capitalize()} must be a list.')
    for p in value.get('projects', [])[:100]:
        if not isinstance(p, dict):
            continue
        data['projects'].append({
            'id': clean_text(p.get('id'), 80) or secrets.token_hex(8),
            'title': clean_text(p.get('title'), 180), 'description': clean_text(p.get('description'), 3000),
            'tech': [clean_text(x, 60) for x in p.get('tech', [])[:30] if clean_text(x,60)],
            'status': clean_text(p.get('status'), 40), 'repo': clean_url(p.get('repo')),
            'demo': clean_url(p.get('demo')), 'icon': clean_text(p.get('icon'), 12),
            'cover': clean_text(p.get('cover'), 24), 'published': bool(p.get('published', True))
        })
    for s in value.get('skills', [])[:100]:
        if not isinstance(s, dict):
            continue
        try: level = max(0, min(100, int(s.get('level', 0))))
        except (TypeError, ValueError): level = 0
        data['skills'].append({'name': clean_text(s.get('name'),100), 'level': level, 'category': clean_text(s.get('category'),80)})
    for cert in value.get('certificates', [])[:100]:
        if isinstance(cert, dict):
            data['certificates'].append({'name':clean_text(cert.get('name'),300),'issuer':clean_text(cert.get('issuer'),300),'date':clean_text(cert.get('date'),100),'credential':clean_url(cert.get('credential'))})
    resume = value.get('resume') if isinstance(value.get('resume'), dict) else {}
    data['resume'] = {key: clean_text(resume.get(key),4000) for key in ('summary','experience','achievements')}
    return data


class Handler(BaseHTTPRequestHandler):
    server_version = 'PortfolioOS'
    sys_version = ''

    def log_message(self, fmt, *args):
        print(f'{self.client_address[0]} - {fmt % args}')

    def send_json(self, status: int, payload: dict, extra_headers=None):
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.security_headers()
        if extra_headers:
            for key, val in extra_headers: self.send_header(key, val)
        self.end_headers()
        self.wfile.write(body)

    def security_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Referrer-Policy', 'strict-origin-when-cross-origin')
        self.send_header('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
        if self.headers.get('X-Forwarded-Proto', '').split(',')[0].strip().lower() == 'https':
            self.send_header('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')

    def body_json(self):
        if not self.headers.get('Content-Type', '').lower().startswith('application/json'):
            raise ValueError('Send this request as JSON.')
        try:
            size = int(self.headers.get('Content-Length', '0'))
        except ValueError as exc:
            raise ValueError('The request length is invalid.') from exc
        if size < 0 or size > MAX_BODY:
            raise ValueError('Request is too large.')
        raw = self.rfile.read(size)
        try:
            value = json.loads(raw or b'{}')
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError('Request body must contain valid JSON.') from exc
        if not isinstance(value, dict):
            raise ValueError('Request body must be a JSON object.')
        return value

    def csrf_ok(self):
        origin = self.headers.get('Origin')
        if origin:
            try:
                parsed = urlparse(origin)
                host = self.headers.get('Host', '')
                return parsed.netloc.lower() == host.lower() and parsed.scheme in ('http', 'https')
            except ValueError:
                return False
        return self.headers.get('Sec-Fetch-Site', '').lower() not in ('cross-site', 'same-site')

    def session_id(self):
        jar = cookies.SimpleCookie(self.headers.get('Cookie', ''))
        morsel = jar.get('portfolio_session')
        if not morsel: return None
        value = morsel.value
        try: sid, sig = value.split('.', 1)
        except ValueError: return None
        expected = hmac.new(SESSION_SECRET.encode(), sid.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected): return None
        now = int(time.time())
        digest = hashlib.sha256(sid.encode()).hexdigest()
        with connect() as db:
            cursor = db.execute('UPDATE sessions SET last_seen_at=? WHERE token_hash=? AND expires_at>?', (now, digest, now))
        return sid if cursor.rowcount == 1 else None

    def require_owner(self):
        return self.session_id() is not None

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/health':
            self.send_json(200, {'ok': True, 'service': 'Crackers portfolio'})
        elif path == '/api/session':
            self.send_json(200, {'authenticated': self.require_owner()})
        elif path == '/api/data':
            if not self.require_owner(): return self.send_json(401, {'error':'Sign in to edit your portfolio.'})
            self.send_json(200, load_data())
        elif path == '/api/portfolio':
            data = load_data()
            self.send_json(200, {'profile':data['profile'],'projects':[p for p in data['projects'] if p.get('published', True)],'skills':data['skills'],'certificates':data['certificates'],'resume':data['resume']})
        elif path in ('/', '/portfolio'):
            html = (ROOT / 'index.html').read_bytes()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(html)))
            self.send_header('Cache-Control', 'no-cache')
            self.security_headers()
            self.end_headers()
            self.wfile.write(html)
        else:
            self.send_json(404, {'error':'Not found.'})

    def do_POST(self):
        if not self.csrf_ok(): return self.send_json(403, {'error':'Request origin was rejected.'})
        path = urlparse(self.path).path
        if path == '/api/login':
            now = time.time(); ip = self.client_address[0]
            ATTEMPTS[ip] = [t for t in ATTEMPTS.get(ip, []) if now-t < 300]
            if len(ATTEMPTS[ip]) >= 8: return self.send_json(429, {'error':'Too many sign-in attempts. Try again in a few minutes.'})
            try:
                supplied_value = self.body_json().get('password', '')
                if not isinstance(supplied_value, str):
                    raise ValueError('Password must be text.')
                supplied = supplied_value
            except ValueError as exc:
                return self.send_json(400, {'error': str(exc)})
            if not ADMIN_PASSWORD or not hmac.compare_digest(supplied.encode(), ADMIN_PASSWORD.encode()):
                ATTEMPTS[ip].append(now)
                return self.send_json(401, {'error':'That password did not match.'})
            ATTEMPTS[ip] = []
            sid = secrets.token_urlsafe(32)
            now_int = int(now)
            with connect() as db:
                db.execute('INSERT INTO sessions(token_hash,created_at,last_seen_at,expires_at) VALUES(?,?,?,?)', (hashlib.sha256(sid.encode()).hexdigest(), now_int, now_int, now_int + SESSION_TTL))
            sig = hmac.new(SESSION_SECRET.encode(), sid.encode(), hashlib.sha256).hexdigest()
            forwarded_proto = self.headers.get('X-Forwarded-Proto', '').split(',')[0].strip().lower()
            secure = '; Secure' if forwarded_proto == 'https' else ''
            cookie = f'portfolio_session={sid}.{sig}; Path=/; HttpOnly; SameSite=Strict; Max-Age={SESSION_TTL}{secure}'
            return self.send_json(200, {'ok':True}, [('Set-Cookie',cookie)])
        if path == '/api/logout':
            sid = self.session_id()
            if sid:
                with connect() as db:
                    db.execute('DELETE FROM sessions WHERE token_hash=?', (hashlib.sha256(sid.encode()).hexdigest(),))
            return self.send_json(200, {'ok':True}, [('Set-Cookie','portfolio_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0')])
        self.send_json(404, {'error':'Not found.'})

    def do_PUT(self):
        if not self.csrf_ok(): return self.send_json(403, {'error':'Request origin was rejected.'})
        if urlparse(self.path).path != '/api/data': return self.send_json(404, {'error':'Not found.'})
        if not self.require_owner(): return self.send_json(401, {'error':'Your session expired. Sign in again.'})
        try:
            data = validate_data(self.body_json())
            save_data(data)
            self.send_json(200, {'ok':True, 'savedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self.send_json(400, {'error':str(exc) or 'Portfolio data is invalid.'})
        except sqlite3.Error:
            self.send_json(500, {'error':'The portfolio could not be saved. Try again shortly.'})


def main():
    if len(ADMIN_PASSWORD) < 14:
        raise SystemExit('Set PORTFOLIO_ADMIN_PASSWORD to at least 14 characters before starting the server. See README.md.')
    if len(os.environ.get('PORTFOLIO_SESSION_SECRET', '')) < 32:
        raise SystemExit('Set PORTFOLIO_SESSION_SECRET to a persistent random value with at least 32 characters. See README.md.')
    init_db()
    server = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    print(f'PortfolioOS ready at http://localhost:{PORT}')
    server.serve_forever()


if __name__ == '__main__':
    main()

