import json
import os
import subprocess
import sys

import requests

EDITOR = os.environ.get("EDITOR", "vim")


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
    with open("/tmp/bbb", "w") as f:
        print(input_text, file=f)
    if os.path.exists("/tmp/bbb.done"):
        os.remove("/tmp/bbb.done")
    os.mkfifo("/tmp/bbb.done")
    subprocess.run(
        "tmux new-window 'vim /tmp/bbb && cat /tmp/bbb > /tmp/bbb.done'",
        shell=True,
    )
    with open("/tmp/bbb.done") as f:
        print("".join(f.readlines()))


def main(server_port, events):
    original_events = get_original_events(server_port)
    ids = get_ids_from_events(events)
    filtered_original_events = get_filtered_original_events(original_events, ids)
    input_text = get_input_text(filtered_original_events)
    execute_editor(input_text)


if __name__ == "__main__":
    server_port = sys.argv[1]
    events = sys.argv[2:]
    main(server_port, events)
