import datetime
import os
import pickle
import sys

import dateutil.parser
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import calendar_info
import vacation_info

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


def create_event_obj(event, start):
    def add_hours(start, hours):
        start_dt = dateutil.parser.parse(start["dateTime"])
        end_dt = start_dt + datetime.timedelta(hours=hours)
        end = {"dateTime": end_dt.isoformat()}
        return end

    end = add_hours(start, event["hour"])
    return {
        "summary": event["summary"],
        "start": start,
        "end": end,
    }


def create_events_obj(date, events):
    new_events = []
    start = {"dateTime": f"{date}T10:00:00+09:00"}
    for event in events:
        new_events.append(create_event_obj(event, start))
        start = new_events[-1]["end"]
    return new_events


def create_vacation_events(date):
    events = vacation_info.events
    return create_events_obj(date, events)


def register(calendar_service, event):
    calendar_service.events().insert(
        calendarId=CALENDAR_IDS["jisseki"], body=event
    ).execute()
    return True


def main():
    date = sys.argv[1]
    calendar_service = get_calendar_service()
    events = create_vacation_events(date)
    for event in events:
        print(event)
        register(calendar_service, event)


if __name__ == "__main__":
    main()


def test_create_event_obj():
    event = {"summary": "休", "hour": 3}
    start = {"dateTime": "2023-09-29T10:00:00+09:00"}
    response = create_event_obj(event, start)
    expected = {
        "summary": "休",
        "start": {"dateTime": "2023-09-29T10:00:00+09:00"},
        "end": {"dateTime": "2023-09-29T13:00:00+09:00"},
    }
    assert response == expected
