from shutil import ignore_patterns
import seaborn
import numpy, scipy, sklearn
import librosa
import os

import requests

import time
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

if __name__ == "__main__":  # pattern matcher
    patterns = ["*"]
    ignore_patterns = None
    ignore_directories = True
    case_sensitive = False
    my_event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)

# Setting values for the observer
path = "./tracks"
go_recursively = True
my_observer = Observer()
my_observer.schedule(my_event_handler, path, recursive=go_recursively)


def on_created(event):
    print(f"hey, {event.src_path} has been created!")
    scanner()


def scanner():
    directory = os.fsencode(path)
    print("Path: " + path)

    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        if ".aif" in filename:
            print("Analysing: " + filename)

            full_name = path + "/" + filename
            print("full_name: " + full_name)

            x, sr = librosa.load(full_name)

            tempo = librosa.beat.tempo(x, sr=sr)
            # print("Tempo: " + tempo)

            db_post(
                {
                    "fileName": filename,
                    "tempo": tempo[0]
                }
            )


def on_deleted(event):
    print(f"hey, {event.src_path} has been deleted!")
    scanner()


def db_post(payload):
    print("Posting", payload)
    r = requests.post("http://localhost:6001/api/tracks", data=payload)
    # preflight, checks = cors.preflight.prepare_preflight(r)
    print(r.text)
    print(r.headers)
    print(r)

    print("Post complete!")


my_event_handler.on_created = on_created
my_event_handler.on_deleted = on_deleted

scanner()

my_observer.start()
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    my_observer.stop()
    my_observer.join()
