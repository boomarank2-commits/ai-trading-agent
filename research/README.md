# Offline research scheduler

`Start-ResearchDesk.ps1` contains a prototype for turning the upstream role files into repeatable
Codex research jobs. **Autonomous execution is hard-disabled in this checkout.** Only `-Status`
works. A Codex `workspace-write` sandbox restricts writes, not reads: under the same Windows user,
the original repository, quarantined holdout, and unrelated home-directory credentials may still
be readable. Prompt instructions and environment cleanup are not a sufficient isolation boundary.

The prepared design stages only prompts, a Registry snapshot, **pre-holdout** public OHLCV, safe
configs, and the research strategy. Candles at or after `holdout_cutoff_utc` are filtered out, user
MCP configuration is ignored, outputs are validated, and cycles are time-bounded. These controls
remain defense in depth for a future runner; they do not make the current same-user process safe.

The only supported command in this checkout is status:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\research\Start-ResearchDesk.ps1 -Status
```

`-Once` and `-Daemon` terminate immediately with `AUTONOMOUS_RESEARCH_DISABLED`
before a workspace or child process is created. Enabling cycles requires a separate
low-privilege OS account, VM, or container that cannot read the host repository/home,
mounts only staged inputs, uses a host-controlled no-follow output channel, and places
the complete Codex process tree in a kill-on-close job/cgroup.

The prepared collector accepts only regular, non-linked files, limits total bytes, and would copy
at most one candidate pair plus one report into `research/inbox/<timestamp>-<role>/` for human
review. Nothing is designed to be automatically registered, promoted, or executed. This path is
currently unreachable because the execution guard fires before workspace creation.

The prototype includes a timeout and atomic single-instance handle, but these are not a substitute
for a Windows Job Object or container cgroup that kills every descendant. Do not install it as a
service or remove the fail-closed guard. Role intervals in `desk.json` are planning data only.

The prototype would use the installed Codex CLI and existing Codex authentication; it never needs
an exchange API key. It must not be enabled under a Windows account that can read the real holdout
or unrelated credentials.
