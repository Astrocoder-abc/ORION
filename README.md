# Orion

Native Python desktop app for **authorized** security assessments, with offline voice.
Run `python main.py`. Everything optional degrades gracefully; nothing needs the internet or an AI model.

## Install

    pip install -r requirements.txt          # vosk, sounddevice, pyttsx3, psutil (all optional)
    # Linux: sudo apt install python3-tk libportaudio2 espeak-ng
    # Voice: unzip a Vosk model (e.g. vosk-model-small-en-us-0.15) into models/
    python main.py              # desktop app
    python main.py status       # component health, no window

## First assessment (typed; voice works for everything except authorization)

    new assessment audit my project for exposed secrets
    scope add C:\code\myapp          (or a folder, IP, CIDR, hostname, *.domain)
    scope exclude C:\code\myapp\vendor
    confirm authorization            (typed or UI button only; voice is refused)
    simulate audit                   (preview; nothing touched)   ->  go ahead
    audit                            (read-only local repository audit)
    findings / explain finding 1 / generate report / retest

Network discovery (`discover 10.0.0.0/28 ports 22,80`) needs Nmap installed and always asks for your
approval (`approve` / `deny`). `stop the current task` cancels tasks; `emergency stop` blocks all new
actions until `resume operations`.

## Voice (fully offline)

**Setup, once:** `python main.py voice-check` lists every requirement and the exact fix for anything missing.
You need one recognition engine plus text-to-speech:

| Piece | Windows | Linux |
|---|---|---|
| Microphone library | `pip install sounddevice` (bundles PortAudio) | `sudo apt install libportaudio2` + pip |
| Speech output | built-in SAPI5 voices | `sudo apt install espeak-ng` |
| Engine A, Vosk (streaming, light) | `pip install vosk` + unzip `vosk-model-small-en-us-0.15` into `models/` | same |
| Engine B, whisper.cpp (more accurate, heavier) | a `whisper-cli` build + `ggml-base.en.bin` in `models/` (or set `whisper_binary` / `whisper_model` in config.json) | same |

`stt_engine` = `auto` (Vosk first, then whisper.cpp), `vosk` or `whisper`; switch live with `engine whisper`.
Compare them on your hardware with a recording: `python main.py voice-bench sample.wav`
(16 kHz mono WAV; reports load time, real-time factor and the text each engine heard).
`python main.py voice-listen` is a headless microphone test: it prints what it hears and whether it would be used, and executes nothing.

**Using it**
- Listen button / Ctrl+L; Esc stops instantly. The meter and state ("listening", "hearing you", "recognising…") are live.
- Typed commands are answered aloud too (Speech button / Ctrl+M or `mute`). Long output is summarised, not read.
- Say **stop** while Orion talks to interrupt it (barge-in). `repeat that` repeats the last reply.
- Orion ignores audio that overlaps its own voice, except "stop".
- `wake word on`: only act on speech containing "Orion". Everything heard is listed in the Voice tab with the reason when it was ignored.
- The microphone turns itself off after 10 minutes without speech (`idle_timeout_s`).
- Set up: `list microphones`, `use microphone 2`, `test microphone`, `calibrate microphone`, `list voices`, `speech voice 3`,
  `speech rate 170`, `speech faster|slower`, `speech volume 80`, `vocabulary commands` (Vosk hears only command words: fewer mistakes, no free speech), `voice status`, `voice check`.
- Speaking targets: type `bookmark add myapp = C:\code\myapp` once, then say "scope add myapp" or "audit myapp".
  Voice can only add bookmarked names to the scope, and can never confirm authorization.

**Offline installation bundle**
1. On a machine with internet, for each target OS / Python version: `python scripts/prepare_offline.py`
   (add `--whisper-binary-url <zip>` to include a whisper.cpp build). It makes `dist/Orion-offline-<os>-py<ver>.zip`.
2. On the target: unzip, then `python scripts/install_offline.py` (checks every file's SHA-256, OS and Python version, then installs with `--no-index`).
3. Linux still needs `libportaudio2 espeak-ng python3-tk` from your package manager; pip cannot bundle system libraries.

## The interface

- **The belt** (top centre): Orion's three belt stars are the three gates every action must pass: scope defined, authorization confirmed, clear to run.
  They light from live engine state (amber while approvals wait, red during an emergency stop), and a light travels along them only while a task is running.
- **The sky** (Overview): every finding is a star. Band and size show severity; shape shows validation: filled = confirmed, ring = potential and not yet validated,
  teal diamond = fixed and verified. Findings on the same file or host are joined like a constellation. Click a star to open it.
- **Next step** (Overview, bottom right) always reflects the real state of the assessment, with a button that does it.
- **Command line**: live suggestions as you type, Tab completes, Up/Down recalls history, Ctrl+K focuses it.
- Views: Ctrl+1..7. Text size: Ctrl+= / Ctrl+- (or `larger text`). `reduced motion on` stops all animation. Minimal mode hides the side panel.

## Safety model (enforced in the backend, not the UI)

- One authorization engine (`orion/security/authorization.py`) decides every action from any source (typed, voice, UI, AI).
- Unknown actions are refused: there is no "run this command" action and no shell.
- Out-of-scope or excluded targets are refused; exclusions win; hostnames are never resolved; scope changes revoke authorization.
- Active actions need approval, which only a human source can grant. Authorization itself cannot be given by voice.
- Every action is re-checked at execution time. Emergency stop blocks new work and reports which tasks really stopped.
- Audit trail (`audit.jsonl`), secret redaction in logs/evidence/reports, tool args validated, output and time capped.

## Honest results

Validation states are kept distinct (confirmed / potential / inconclusive / not tested / tested no issue / not reproduced /
remediated / retested verified). Pattern matches are *potential*. Reports list what was not tested
(for example known-vulnerable package versions, git history) and mark partial runs as partial.

## Layout

    main.py                    entry point
    orion/core/                config, logging, events, health, Application
    orion/security/            scope, authorization, approvals, audit, redaction, emergency stop
    orion/assessment/          lifecycle, tasks, rules knowledge
    orion/tools/               registry, subprocess adapter, nmap adapter, repository audit
    orion/evidence/            models, SQLite store
    orion/reporting/           Markdown + JSON generator
    orion/ai/                  optional advisory provider (rules; local OpenAI-compatible server)
    orion/voice/               microphone + Vosk, pyttsx3, wake word / speech text helpers
    orion/ui/app.py            Tkinter command centre
    tests/                     pytest (python -m pytest)

Data lives in `%APPDATA%\orion` / `~/.config/orion` (database, evidence, reports, audit trail, logs).

## Not built yet

Remote agents, cloud/AD/web/API domains, password auditing and exploit validation, a dedicated wake-word model
(wake word is currently a text match on the transcript). Not exercised on real hardware by the author: a live microphone with a
speech model, whisper.cpp itself, Nmap, and Windows.
