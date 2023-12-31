#!/usr/bin/env python
import argparse
import os
import pickle
import subprocess
import sys
from datetime import datetime, timedelta
from http.server import HTTPServer
from subprocess import PIPE

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import calendar_info
# import convert_format
# import fzf_options
import internal_server

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PICKLE_PATH = f"{SCRIPT_DIR}/GoogleCalendarApi.pickle"
CALENDAR_IDS = calendar_info.CALENDAR_IDS

calendar_service = None


def get_start(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d")


def get_end(start):
    return start + timedelta(days=1)


def get_calendar_service():
    creds = None
    if os.path.exists(PICKLE_PATH):
        with open(PICKLE_PATH, "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json", "https://www.googleapis.com/auth/calendar"
        )
        creds = flow.run_local_server(port=0)
        with open(PICKLE_PATH, "wb") as token:
            pickle.dump(creds, token)
    return build("calendar", "v3", credentials=creds)


def get_events(start, end):
    global calendar_service
    if not calendar_service:
        calendar_service = get_calendar_service()

    events_result = (
        calendar_service.events()
        .list(
            calendarId=CALENDAR_IDS["primary"],
            timeMin=start.isoformat() + "Z",
            timeMax=end.isoformat() + "Z",
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return events_result.get("items", [])


def get_visible_events(events):
    return [
        f'{e["id"]} {e["start"]["dateTime"]} {e["end"]["dateTime"]} {e["summary"]}'
        for e in events
    ]


def get_event_for_stdout(event):
    sp = event.split(" ")
    return f'{sp[1]} {" ".join(sp[3:])}'


def execute_fzf(events, server_port, fzf_port):
    cmd = [
        "fzf",
        "--listen",
        str(fzf_port),
        "--multi",
        "--reverse",
        "--print-query",
        "--expect",
        "enter",
        "--with-nth",
        "2,4..",
        "--bind",
        f"alt-e:execute-silent(python {SCRIPT_DIR}/calendar_editor.py {server_port} {{+}})",
    ]

    proc = subprocess.run(cmd, input="\n".join(events), stdout=PIPE, text=True)
    return proc.stdout


def find_available_port():
    httpd = HTTPServer(("", 0), None)
    return httpd.server_port


def main(args, options):
    start = get_start(args[1])
    end = get_end(start)
    original_events = get_events(start, end)
    visible_events = get_visible_events(original_events)

    server_port = internal_server.start_server(original_events)
    fzf_port = find_available_port()
    internal_server.set_fzf_port(fzf_port)
    internal_server.set_original_events(original_events)

    stdout = execute_fzf(visible_events, server_port, fzf_port)
    if len(stdout.strip()) > 0:
        sp = stdout.split("\n")
        # query = sp[0]
        key = sp[1]
        events = sp[2:-1]

        print("\n".join([get_event_for_stdout(e) for e in events]))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("target_date")
    args = p.parse_args()
    main(sys.argv, args.__dict__)
