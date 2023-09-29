import os
import pickle
import sys
from datetime import datetime, timedelta

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import calendar_info

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PICKLE_PATH = f"{SCRIPT_DIR}/GoogleCalendarApi.pickle"
CALENDAR_IDS = calendar_info.CALENDAR_IDS


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


def get_start(date_str):
    return datetime.strptime(date_str, "%Y-%m-%d")


def get_end(start):
    return start + timedelta(days=1)


def collect_events(calendar_service, start, end):
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


def filter_event(event):
    summary = event["summary"]
    if summary.startswith("[離席]"):
        return False
    return True


def get_jisseki_event(event):
    keys = ["summary", "start", "end"]
    return {k: event[k] for k in event.keys() if k in keys}


def register_to_jisseki(calendar_service, jisseki_event):
    calendar_service.events().insert(
        calendarId=CALENDAR_IDS["jisseki"], body=jisseki_event
    ).execute()
    return True


calendar_service = get_calendar_service()
start = get_start(sys.argv[1])
end = get_end(start)
events = collect_events(calendar_service, start, end)
for event in events:
    if filter_event(event):
        print(event["summary"])
        jisseki_event = get_jisseki_event(event)
        register_to_jisseki(calendar_service, jisseki_event)
