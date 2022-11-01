from shutil import ignore_patterns
import seaborn
import numpy, scipy, sklearn
import librosa
import os

import requests

import time
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

url = 'http://localhost:5000/api/msg' # URL for the local express API

if __name__ == "__main__": # pattern matcher
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

    directory = os.fsencode(directory_in_str)

    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        print("Analysing: " + filename)

def dbPost(payload):
    r = requests.post("http://localhost:6000/api/tracks", data = payload)
    print(r.text)

def getCentroid(file):
    print("Getting centroid for: " + file)

def getBandwidth(file):
    print("Getting bandwidth for: " + file)

def getContrast(file):
    print("Getting contrast for: " + file)

def getTempo(file):
    print("Getting tempo for: " + file)

def getGenre(file):
    print("Getting genre for: " + file)

my_event_handler.on_created = on_created

my_observer.start()
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    my_observer.stop()
    my_observer.join()



