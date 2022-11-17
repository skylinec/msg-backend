from shutil import ignore_patterns
import numpy
import librosa
import os

import requests

import time
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

from pydub import AudioSegment

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
    clear_db()
    print(f"hey, {event.src_path} has been created!")
    scanner()

def scanner():
    directory = os.fsencode(path)
    print("Path: " + path)

    for file in os.listdir(directory):
        file_name = os.fsdecode(file)
        if ".aif" in file_name:
            print("Analysing: " + file_name)

            full_name = path + "/" + file_name
            print("full_name: " + full_name)

            x, sr = librosa.load(full_name)

            tempo = librosa.beat.tempo(x, sr=sr)
            # print("Tempo: " + tempo)

            genre = ""

            contrast = librosa.feature.spectral_contrast(x, sr=sr)
            chroma_stft = librosa.feature.chroma_stft(x, sr=sr)
            rmse = librosa.feature.rms(x)
            spec_cent = librosa.feature.spectral_centroid(x, sr=sr)
            spec_bw = librosa.feature.spectral_bandwidth(x, sr=sr)
            rolloff = librosa.feature.spectral_rolloff(x, sr=sr)
            zcr = librosa.feature.zero_crossing_rate(x)
            mfcc = librosa.feature.mfcc(x, sr=sr)

            chroma_stft_mean = int(numpy.mean(chroma_stft))
            contrast_mean = int(numpy.mean(contrast))
            rmse_mean = int(numpy.mean(rmse))
            spec_cent_mean = int(numpy.mean(spec_cent))
            spec_bw_mean = int(numpy.mean(spec_bw))
            rolloff_mean = int(numpy.mean(rolloff))
            zcr_mean = int(numpy.mean(zcr))

            adj_tempo = int(tempo[0])

            db_post(
                {
                    "fileName": file_name,
                    "genre": genre,
                    "tempo": adj_tempo,
                    "rmse": rmse_mean,
                    "contrast": contrast_mean,
                    "centroid": spec_cent_mean,
                    "bandwidth": spec_bw_mean,
                    "rolloff": rolloff_mean,
                }
            )


def on_deleted(event):
    clear_db()
    print(f"hey, {event.src_path} has been deleted!")
    scanner()


def db_post(payload):
    print("Posting", payload)
    headers = {'Content-Type': 'application/json'}
    r = requests.post("http://localhost:6001/api/tracks", json=payload, headers=headers)
    # preflight, checks = cors.preflight.prepare_preflight(r)
    print("Text", r.text)
    print("Headers", r.headers)
    print("Whole request",r)

    print("Post complete!")

def clear_db():
    r = requests.post("http://localhost:6001/api/cleartracks", json={})

    print("Text", r.text)
    print("Headers", r.headers)
    print("Whole request",r)

    print("Clear database complete!")


my_event_handler.on_created = on_created
my_event_handler.on_deleted = on_deleted

clear_db()

scanner()

my_observer.start()
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    my_observer.stop()
    my_observer.join()
