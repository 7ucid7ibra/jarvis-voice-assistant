#!/usr/bin/env python3
import os
import sys
import multiprocessing as mp


def main() -> None:
    sys.path.insert(0, os.path.dirname(__file__))
    from jarvis_assistant.main import main as jarvis_main

    jarvis_main()


if __name__ == "__main__":
    mp.freeze_support()
    main()
