#!/usr/bin/env python3
"""A minimal stand-in forum for Week 3 Exercise 2.

Why this exists: UPC Àrtemis is behind institutional SSO with the Moodle
web-services token flow disabled for students, so neither road could reach it.
This server is a local stand-in that both roads post to, so the CLI-vs-browser
token comparison — the actual point of the exercise — is unaffected.

It gives each road a real target:
  - CLI road    -> POST /api/post   (token-gated JSON, one curl call)
  - browser road-> GET  /           (an HTML page with a form to drive)

No database, no dependencies beyond the standard library. Posts live in memory
and in posts.json next to this file, so a reply-to-an-existing-post flow works.

Run:
    python forum_server.py
Then the forum is at http://localhost:8099/ and the token is printed at start.
"""

import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

HOST = "127.0.0.1"
PORT = 8099
TOKEN = os.environ.get("FORUM_TOKEN", "playground-token-2026")
STORE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "posts.json")


def load_posts():
    try:
        with open(STORE) as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_posts(posts):
    with open(STORE, "w") as handle:
        json.dump(posts, handle, indent=2)


def add_post(author, message, reply_to=None):
    posts = load_posts()
    post = {
        "id": len(posts) + 1,
        "author": author or "anonymous",
        "message": message,
        "reply_to": reply_to,
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    posts.append(post)
    save_posts(posts)
    return post


def render_page():
    posts = load_posts()
    if posts:
        items = "\n".join(
            f"<li><b>#{p['id']} {p['author']}</b> "
            f"<small>{p['ts']}</small>"
            + (f" <em>(reply to #{p['reply_to']})</em>" if p.get("reply_to") else "")
            + f"<br>{p['message']}</li>"
            for p in posts
        )
    else:
        items = "<li><em>No posts yet. Be the first agent.</em></li>"
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Agents Playground Forum</title></head>
<body>
<h1>Agents Playground Forum</h1>
<p>A local stand-in for the Àrtemis playground forum.</p>
<h2>Posts</h2>
<ul id="posts">{items}</ul>
<h2>New post</h2>
<form method="POST" action="/post">
  <label>Author: <input name="author" id="author"></label><br>
  <label>Reply to (optional post id): <input name="reply_to" id="reply_to"></label><br>
  <label>Message:<br><textarea name="message" id="message" rows="3" cols="50"></textarea></label><br>
  <button type="submit" id="submit">Post</button>
</form>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, content_type="text/html; charset=utf-8"):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/api/posts"):
            self._send(200, json.dumps(load_posts()), "application/json")
        elif self.path in ("/", "/index.html"):
            self._send(200, render_page())
        else:
            self._send(404, "not found")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode()

        # CLI road: token-gated JSON API
        if self.path == "/api/post":
            if self.headers.get("Authorization") != f"Bearer {TOKEN}":
                self._send(401, json.dumps({"error": "bad or missing token"}),
                           "application/json")
                return
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                self._send(400, json.dumps({"error": "invalid json"}),
                           "application/json")
                return
            if not payload.get("message"):
                self._send(400, json.dumps({"error": "message required"}),
                           "application/json")
                return
            post = add_post(payload.get("author"), payload["message"],
                            payload.get("reply_to"))
            self._send(200, json.dumps({"ok": True, "post": post}),
                       "application/json")
            return

        # Browser road: HTML form submit (no token; a logged-in browser session)
        if self.path == "/post":
            form = parse_qs(raw)
            message = (form.get("message") or [""])[0]
            author = (form.get("author") or [""])[0]
            reply_to = (form.get("reply_to") or [""])[0] or None
            if message:
                add_post(author, message, reply_to)
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
            return

        self._send(404, "not found")

    def log_message(self, *args):
        pass  # keep the console quiet; the meter is what we watch


if __name__ == "__main__":
    print(f"Agents Playground Forum (stand-in)")
    print(f"  URL   : http://{HOST}:{PORT}/")
    print(f"  token : {TOKEN}")
    print(f"  store : {STORE}")
    print("  Ctrl+C to stop.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
