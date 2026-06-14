# ▶️ HOWTORUN — Homework 5 MCP Servers

Step-by-step setup for the four MCP servers in **Claude Code**. Everything is
registered in the project-level [`.mcp.json`](./.mcp.json); the `claude mcp add`
commands below produce exactly that file (scope `project`).

All commands assume this directory is your project root:

```
/Users/admin/projects/SET/gen-ai-software-engineering/homework-5
```

---

## 0. Secrets first 🔐

Never hardcode tokens. Copy the template and fill in real values:

```bash
cp .env.example .env
$EDITOR .env          # add your real GITHUB_PAT
```

Only **GitHub** needs a secret in `.env` — Jira uses **OAuth** (browser sign-in,
no token to store) and filesystem/lorem need none. Export `GITHUB_PAT` into the
shell **before** launching Claude Code so the `${VAR}` placeholder in `.mcp.json`
resolves:

```bash
set -a; source .env; set +a
```

`.env` is git-ignored; only `.env.example` is committed.

---

## 1. Custom FastMCP server — install & test ✍️

```bash
cd custom-mcp-server

# create an isolated venv (Python 3.10+ required by FastMCP; we used 3.13)
/opt/homebrew/bin/python3.13 -m venv .venv

# install dependencies (requirements.txt explicitly lists fastmcp)
./.venv/bin/pip install -r requirements.txt

# ✅ verify it works in-process: asserts 5 words and 30 words exactly
./.venv/bin/python test_server.py
```

Expected output:

```
read(word_count=5)  -> 5 words: 'Lorem ipsum dolor sit amet'
read()              -> 30 words: 'Lorem ipsum dolor sit amet consectetur ...'
lorem://text/7      -> 7 words: 'Lorem ipsum dolor sit amet consectetur adipiscing'

All assertions passed ✅  (5 == 5, 30 == 30, 7 == 7)
```

**Startup command** (what Claude Code runs as a stdio subprocess — default
transport is stdio, so no extra flags are needed):

```bash
/Users/admin/projects/SET/gen-ai-software-engineering/homework-5/custom-mcp-server/.venv/bin/python \
  /Users/admin/projects/SET/gen-ai-software-engineering/homework-5/custom-mcp-server/server.py
```

`cd ..` back to the project root before the next steps.

---

## 2. Register all four servers with `claude mcp add` 🧩

> These write to the **project** scope → `.mcp.json` in this directory.
> The repo already ships a ready-made `.mcp.json`; run these only if you want to
> regenerate it (or skip them and just keep the committed file).

### 2a. GitHub (remote HTTP, PAT) 🐙

```bash
claude mcp add --transport http --scope project github \
  https://api.githubcopilot.com/mcp/ \
  --header "Authorization: Bearer ${GITHUB_PAT}"
```

- Endpoint: `https://api.githubcopilot.com/mcp/` (GitHub's hosted remote server).
- The old npm `@modelcontextprotocol/server-github` is **deprecated** — do not use it.
- PAT scopes: `repo`, `read:org` (add more if you want write actions).

### 2b. Filesystem (local stdio) 📁

```bash
claude mcp add --scope project filesystem -- \
  npx -y @modelcontextprotocol/server-filesystem \
  /Users/admin/projects/SET/gen-ai-software-engineering/homework-5
```

- Package: `@modelcontextprotocol/server-filesystem` (run via `npx -y`).
- The trailing **absolute** path is the only directory the server may touch.

### 2c. Jira / Atlassian Rovo (remote HTTP, OAuth 2.1) 🪲

```bash
claude mcp add --transport http --scope project jira \
  https://mcp.atlassian.com/v1/mcp
```

- Endpoint: `https://mcp.atlassian.com/v1/mcp` (current HTTP/streamable server).
- Auth: **OAuth 2.1** — no header, no secret in `.env`. On first use, run `/mcp`
  inside Claude Code, pick `jira`, and complete the browser sign-in; Claude Code
  stores and refreshes the token automatically.
- ⚠️ Do **not** use the legacy `…/v1/sse` endpoint (unsupported after 2026-06-30).

> **Why OAuth and not an API token?** The homework's "last 5 bugs" request needs
> Jira's JQL search tool (`searchJiraIssuesUsingJql`). The Atlassian Rovo server
> only exposes that under OAuth — its **API-token (Basic auth) mode exposes only
> Teamwork Graph relationship tools, with no JQL/issue-search**. So OAuth is
> required to satisfy Task 3. (TASKS.md imposes no API-token requirement; it just
> asks for "the required credentials.") To use API-token mode instead, add the
> header `Authorization: Basic ${ATLASSIAN_AUTH_B64}` — but note the query
> limitation above, and that an org admin must enable API-token auth.

### 2d. Custom lorem FastMCP server (local stdio) ✍️

```bash
claude mcp add --scope project lorem -- \
  /Users/admin/projects/SET/gen-ai-software-engineering/homework-5/custom-mcp-server/.venv/bin/python \
  /Users/admin/projects/SET/gen-ai-software-engineering/homework-5/custom-mcp-server/server.py
```

---

## 3. Verify the servers are live ✅

```bash
claude mcp list        # all four should show ✓ Connected
```

Inside a `claude` session you can also run `/mcp` to inspect each server's tools
and resources.

---

## 4. Use / test the `read` tool inside Claude Code 🧪

Ask Claude (the `lorem` server is connected):

> Use the **lorem** server's `read` tool with `word_count=5`.

Expected: `Lorem ipsum dolor sit amet` (exactly 5 words). Ask again with no
argument to get the default 30 words. You can also read the resource directly:
`lorem://text/12`.

---

## 5. Required interactions to capture (screenshots) 📸

| Server | Prompt to run | Screenshot file |
|--------|---------------|-----------------|
| github | "List the 5 most recent commits / PRs on my repo" | `docs/screenshots/github-mcp-result.png` |
| filesystem | "List the files in this directory and read README.md" | `docs/screenshots/filesystem-mcp-result.png` |
| jira | **"Give me the tickets of the last 5 bugs on a project"** | `docs/screenshots/jira-or-notion-mcp-result.png` |
| lorem | "Call the `read` tool with word_count=5" | `docs/screenshots/custom-mcp-read-tool-result.png` |

See [`docs/screenshots/SCREENSHOTS_TODO.md`](./docs/screenshots/SCREENSHOTS_TODO.md)
for exactly what each screenshot must show.

---

## 📚 Resources vs. Tools (quick reference)

- **Resource** = passive data behind a URI that Claude **reads** (no side
  effects), e.g. `lorem://text/{word_count}`. Think `GET`.
- **Tool** = an action Claude **calls** that runs code, e.g. `read(word_count)`.
  Think `POST`. The two can return the same data — the difference is *read* vs.
  *invoke*.
