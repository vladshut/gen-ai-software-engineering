# 🔌 Homework 5 — MCP Servers

**Author:** Vladyslav Shut

This homework wires four **Model Context Protocol (MCP)** servers into
**Claude Code** (the CLI host) and demonstrates a working interaction with each.
All four are registered through the project-level [`.mcp.json`](./.mcp.json).

## 🧩 The four servers

| # | Server | Transport | What it does | Auth |
|---|--------|-----------|--------------|------|
| 1 | **github** 🐙 | remote `http` | Query repos, PRs, issues, commits via GitHub's hosted MCP | `Bearer ${GITHUB_PAT}` |
| 2 | **filesystem** 📁 | local `stdio` | List/read files under the homework-5 directory | none (path-scoped) |
| 3 | **jira** 🪲 | remote `http` | Query Jira/Confluence via Atlassian Rovo MCP | OAuth 2.1 (browser) |
| 4 | **lorem** ✍️ | local `stdio` | Custom **FastMCP** server: a `read` tool + `lorem://text/{n}` resource | none |

> 🐙 GitHub's npm `@modelcontextprotocol/server-github` package is **deprecated
> (Apr 2025)** — this setup uses GitHub's **hosted remote** server at
> `https://api.githubcopilot.com/mcp/` instead.

## 🛠️ Custom server (Task 4)

[`custom-mcp-server/server.py`](./custom-mcp-server/server.py) is built with
[FastMCP](https://github.com/jlowin/fastmcp) and exposes the lorem-ipsum text in
**both** MCP primitives:

- **Resource** — `lorem://text/{word_count}` (and `lorem://text`, default 30) —
  data Claude can *read*.
- **Tool** — `read(word_count: int = 30)` — an action Claude can *call*.

Both return the first `word_count` words of
[`lorem-ipsum.md`](./custom-mcp-server/lorem-ipsum.md). It has been verified
in-process (see [`test_server.py`](./custom-mcp-server/test_server.py)):
`read(word_count=5)` → exactly 5 words, `read()` → exactly 30 words.

### Resources vs. Tools

- **Resources** are *passive data* addressed by a URI that the client **reads**
  (like a `GET`) — files, API payloads, db rows. No side effects.
- **Tools** are *actions* the client **invokes** (like a `POST`) — they run
  code and can have effects. Here `read` is a tool that returns the same
  word-limited text the resource exposes.

## 📂 Layout

```
homework-5/
├── README.md                 ← you are here
├── HOWTORUN.md               ← install / run / connect / test, step by step
├── .mcp.json                 ← all four servers (uses ${ENV_VAR} placeholders)
├── .env.example              ← template for secrets (real .env is git-ignored)
├── custom-mcp-server/
│   ├── server.py             ← FastMCP server (resource + read tool)
│   ├── lorem-ipsum.md        ← 153-word source text
│   ├── requirements.txt      ← explicitly lists fastmcp
│   └── test_server.py        ← in-process client test (5==5, 30==30)
└── docs/screenshots/         ← the 4 required result screenshots
```

## 🤖 How AI built this (and what I verified)

This homework was built **with Claude Code** (Opus) driving the work end-to-end,
with me steering decisions and verifying every result.

**Workflow / prompts used:**
- *"Set up Homework 5 — configure GitHub, Filesystem, Jira and a custom FastMCP
  server"* → Claude scaffolded the repo, fetched the **current** official docs for
  each server (install syntax drifts fast), and wrote `.mcp.json` with `${ENV_VAR}`
  placeholders (no hardcoded secrets).
- *"Register the servers and test them"* → Claude pre-approved the project servers,
  verified my GitHub PAT and Atlassian token with live probes, and ran each MCP
  tool: `list_commits`, filesystem `directory_tree`/`read_text_file`,
  `searchJiraIssuesUsingJql`, and the custom `read` tool.
- *"Give me the last 5 bugs"* → exercised the Jira MCP via JQL.

**What I verified myself (not just trusted the model):**
- The custom server with FastMCP's in-process client: `read(5)` → exactly 5 words,
  `read()` → exactly 30 — see [`test_server.py`](./custom-mcp-server/test_server.py).
- All four servers showing `✔ Connected` in `claude mcp list`.
- Each screenshot in `docs/screenshots/` is a real MCP tool call + result.

**Challenges & how they were addressed:**
- 🐙 **GitHub npm package is dead** (deprecated Apr 2025) → switched to GitHub's
  hosted **remote** MCP server over HTTP with a Bearer PAT.
- 🪲 **Jira API token vs OAuth** — the headless API-token connection only exposes
  *Teamwork Graph* tools (no JQL search), so the "last 5 bugs" request couldn't
  run. Since TASKS.md doesn't mandate API-token auth, I switched the `jira` entry
  to **OAuth 2.1**, which exposes `searchJiraIssuesUsingJql`. (Both approaches are
  documented in [HOWTORUN.md](./HOWTORUN.md).)
- 🐞 The Jira project had no bugs, so 5 sample Bug tickets were created to make the
  query meaningful, then removed after capturing the result.

## 🚀 Getting started

See **[HOWTORUN.md](./HOWTORUN.md)** for the full walkthrough: installing
dependencies, the exact `claude mcp add` command per server, the required
environment variables, and how to test the custom `read` tool.
