import json
import os
import pickle
import subprocess
import sys
import tempfile

import requests
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import calendar_info

EDITOR = os.environ.get("EDITOR", "vim")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PICKLE_PATH = f"{SCRIPT_DIR}/GoogleCalendarApi.pickle"
CALENDAR_IDS = calendar_info.CALENDAR_IDS

calendar_service = None


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


def get_fzf_api_url(server_port):
    return f"http://localhost:{server_port}"


def get_from_localhost(*args, **kwargs):
    return requests.get(*args, **kwargs, proxies={"http": None})


def post_to_localhost(*args, **kwargs):
    return requests.post(*args, **kwargs, proxies={"http": None})


def get_original_events(server_port):
    params = {"get_input": "json"}
    print(server_port, params)
    response = get_from_localhost(get_fzf_api_url(server_port), params=params)
    return json.loads(response.text)


def get_ids_from_events(events):
    return [e.split(" ")[0] for e in events]


def get_filtered_original_events(original_events, ids):
    return [x for x in original_events if x["id"] in ids]


def get_input_text(events):
    return json.dumps(events, indent=4).encode().decode("raw-unicode-escape")


def execute_editor(input_text):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = f"{tmpdir}/event_edit"
        tmppath_done = f"{tmppath}.done"
        with open(tmppath, "w") as f:
            print(input_text, file=f)
        if os.path.exists(tmppath_done):
            os.remove(tmppath_done)
        os.mkfifo(tmppath_done)
        subprocess.run(
            f"tmux new-window 'vim {tmppath} && cat {tmppath} > {tmppath_done}'",
            shell=True,
        )
        with open(tmppath_done) as f:
            return json.load(f)


def update_event(event):
    global calendar_service
    if not calendar_service:
        calendar_service = get_calendar_service()

    calendar_id = CALENDAR_IDS["primary"]
    calendar_service.events().update(
        calendarId=calendar_id, eventId=event["id"], body=event
    ).execute()


def update_events(events):
    for event in events:
        update_event(event)


def main(server_port, events):
    original_events = get_original_events(server_port)
    ids = get_ids_from_events(events)
    filtered_original_events = get_filtered_original_events(original_events, ids)
    input_text = get_input_text(filtered_original_events)
    edited_events = execute_editor(input_text)
    update_events(edited_events)


if __name__ == "__main__":
    server_port = sys.argv[1]
    events = sys.argv[2:]
    main(server_port, events)
