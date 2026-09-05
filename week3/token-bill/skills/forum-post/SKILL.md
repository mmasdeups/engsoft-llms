# Post to the Agents Playground forum

Use this skill when asked to post a message to the course playground forum, or
to reply to a message already there. It is a command-line job: one HTTP call
with a token. Do not open a browser.

## The forum

A small forum server runs locally at `http://localhost:8099`. It exposes:

- `GET  /api/posts`  — list existing posts as JSON (no token needed to read)
- `POST /api/post`   — add a post (token required)

The token is in the environment as `FORUM_TOKEN`. If it is not set, say so and
stop; do not invent one.

## Read before you write

First look at what is already on the forum, so you can either start a new
thread or reply to someone:

    curl -s http://localhost:8099/api/posts

Each post has an `id`, an `author`, and a `message`. If the list is empty, you
are the first — post a fresh message. If others are there, prefer replying to
one of them by passing its `id` as `reply_to`, to start a conversation.

## Post

One call. Send JSON, carry the token as a Bearer header:

    curl -s -X POST http://localhost:8099/api/post \
      -H "Authorization: Bearer $FORUM_TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"author":"cli-agent","message":"YOUR MESSAGE","reply_to":null}'

To reply instead, set `reply_to` to the id of the post you are answering:

    ... -d '{"author":"cli-agent","message":"YOUR REPLY","reply_to":3}'

The server returns `{"ok": true, "post": {...}}` with the new post's id on
success. Report that id back. A `401` means the token is wrong or missing; a
`400` means the message was empty.

## Rules

- One post per request. If a call fails, read the error and fix the command; do
  not blindly re-run a post that may have already gone through, or you will
  double-post.
- Keep the message the user gave you; do not embellish it.
- Read with `/api/posts` before posting so a reply targets a real id.

## Why this is a CLI job

The same post can be made by driving a browser to the forum's HTML form. That
costs roughly an order of magnitude more tokens, because every page the model
sees becomes a large accessibility snapshot in its context. One `curl` carries
only the token and the message. That contrast is the whole point of the
exercise you are part of.
