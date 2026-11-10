#!/usr/bin/env python3
"""Orion entry point.

    python main.py          open the desktop application
    python main.py status   print component health and exit
"""
import argparse
import sys

from orion import __version__


def run_status() -> int:
    from orion.core.application import Application

    app = Application()
    app.start()
    print(app.status_report())
    app.shutdown()
    return 0


def run_voice_check() -> int:
    from orion.core.config import Config, default_data_dir
    from orion.voice.diagnostics import diagnose, format_rows

    print(format_rows(diagnose(Config.load(default_data_dir() / "config.json"))))
    return 0


def run_voice_bench(wav: str, engines) -> int:
    from orion.core.config import Config, default_data_dir
    from orion.voice.bench import format_benchmark, run_benchmark

    try:
        rows = run_benchmark(Config.load(default_data_dir() / "config.json"), wav, engines or None)
    except (OSError, ValueError) as exc:
        print(f"Cannot benchmark: {exc}", file=sys.stderr)
        return 1
    print(format_benchmark(rows))
    return 0


def run_voice_say(text: str) -> int:
    import time

    from orion.core.application import Application

    app = Application()
    app.start()
    if not app.speaker.available:
        print("Speech output unavailable: run 'python main.py voice-check'", file=sys.stderr)
        return 1
    app.speaker.muted = False
    app.speaker.say(text)
    time.sleep(0.3)
    while app.speaker._queue.qsize() or app.speaker.speaking.is_set():
        time.sleep(0.1)
    app.shutdown()
    return 0


def run_voice_listen() -> int:
    """Headless microphone test: prints what is heard and whether it would be used. Executes nothing."""
    import threading
    import time

    from orion.core.application import Application
    from orion.voice.manager import VoiceManager

    app = Application()
    app.start()
    if not app.voice.available:
        print(app.status_report(), file=sys.stderr)
        return 1
    vm = VoiceManager(app.config, app.bus, app.health, lambda t: None, threading.Event(), vocabulary=app._vocabulary)
    vm.engine, vm.available = app.voice.engine, True
    ok, msg = vm.start_listening()
    print(f"{msg} Engine: {vm.engine.name}. Speak; Ctrl+C to quit. (Nothing is executed.)")
    try:
        while vm.listening or app.bus.drain(0):
            for ev in app.bus.drain():
                d = ev.data
                if ev.kind == "partial" and d["text"]:
                    print(f"\r  ... {d['text']:<60}", end="", flush=True)
                elif ev.kind == "heard":
                    print(f"\r  {'USED   ' if d['accepted'] else 'IGNORED'} {d['text']!r} {d['note']}".ljust(80))
                elif ev.kind == "voice_state" and d["state"] in ("loading", "error"):
                    print(f"  [{d['state']}] {d.get('detail', '')}")
            time.sleep(0.1)
            if not vm.listening:
                break
    except KeyboardInterrupt:
        pass
    vm.stop_listening()
    app.shutdown()
    return 0


def run_gui() -> int:
    try:
        import tkinter  # noqa: F401
    except ImportError:
        print("Tkinter is not available. On Debian/Ubuntu: sudo apt install python3-tk", file=sys.stderr)
        return 1
    from orion.ui.app import run

    return run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="orion", description="Orion")
    parser.add_argument("--version", action="version", version=f"Orion {__version__}")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("status", help="print component health and exit")
    sub.add_parser("voice-check", help="check every voice requirement and say how to fix what is missing")
    sub.add_parser("voice-listen", help="headless microphone test; prints what is heard, executes nothing")
    bench = sub.add_parser("voice-bench", help="compare recognition engines on a 16 kHz mono WAV file")
    bench.add_argument("wav")
    bench.add_argument("--engine", action="append", choices=["vosk", "whisper"])
    say = sub.add_parser("voice-say", help="speak text with the offline voice")
    say.add_argument("text", nargs="+")
    args = parser.parse_args(argv)
    if args.command == "status":
        return run_status()
    if args.command == "voice-check":
        return run_voice_check()
    if args.command == "voice-listen":
        return run_voice_listen()
    if args.command == "voice-bench":
        return run_voice_bench(args.wav, args.engine)
    if args.command == "voice-say":
        return run_voice_say(" ".join(args.text))
    return run_gui()


if __name__ == "__main__":
    sys.exit(main())
