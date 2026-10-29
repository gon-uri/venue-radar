# Public And Private Documentation

Reviewed: 2026-10-08.

The public repository must explain how Venue Radar works and how to maintain
it without requiring access to the owner's working notes. `AGENTS.md` and
`project_docs/` remain tracked. The root `private_notes/` directory is ignored
in `.gitignore` and is optional local context, not project infrastructure.

## What Goes Where

| Information | Location |
| --- | --- |
| Simple project description, website, author and license links | Root `README.md` |
| Agent entrypoint and required workflows/checks | `AGENTS.md` |
| Current state, organization, schema, maintenance, additions and publication | Owning guide in `project_docs/` |
| Concise technical rationale and durable constraints | `project_docs/decisions.md` |
| Conference source evidence, uncertainty, publication caveats and deferred candidates | Owning public evidence guide and canonical YAML |
| Verification needed to assess the current release | Dated public status summary, relevant tests, commits and CI results |
| Detailed session diary, agent discussions, personal preferences, brainstorming and unfinished plans | `private_notes/` |
| Rejected wording, font/logo exploration and detailed proposal history | `private_notes/` |

Public ADRs explain technical behavior, not every conversation or personal
choice leading to it. Keep them focused on constraints, rationale and
consequences. Historical source evidence stays public when it is needed to
understand a data decision; do not hide provenance in private notes.

## Agent Workflow

1. Onboard using [AGENTS.md](../AGENTS.md), [the index](README.md) and current
   public guides. A fresh clone without private notes is fully supported.
2. If local context is useful, look for `private_notes/README.md` and the newest
   entries in `private_notes/session_log.md`. Their absence is not a blocker.
   Current source and public requirements take precedence over old notes.
3. After changes, update affected public guides and any material technical ADR.
   Put detailed working history and session checklists in the local log, not
   a new tracked diary. If needed, recreate the ignored directory/log locally.
4. Promote any new requirement, source evidence, unresolved maintenance task or
   verification limitation needed by contributors into its owning public guide.
   Do not require contributors or CI to create/read private files.
5. Before publication, review the tracked diff and confirm that no private
   content is staged. Never force-add this directory.

For example, a rejected font list belongs in private notes; the selected font,
its license, asset ownership and regeneration instructions belong in public
[branding](branding.md) and [development](development.md#branding-tools).

## Privacy And History Limits

Ignoring a path is not encryption, access control or an automatic backup.
Local agents/tools can still read it, and a forced Git add can bypass the rule.
Keep secrets and genuinely sensitive material outside this repository; arrange
a separate backup for useful local notes.

The 2026-10-08 split removes detailed session/design/copy histories from the
current tracked file layout. It does not erase previously published commits,
clones or copies. No Git history rewrite is part of this change. New private
notes stay local unless deliberately copied into public files.

Checks for the boundary:

```sh
git check-ignore private_notes/session_log.md
git ls-files -- private_notes/
git diff --cached --name-only
```

The first should report the ignored path, the second should be empty, and the
third must not contain private notes. Documentation tests also enforce the
ignore rule and ensure public links do not depend on private files.
