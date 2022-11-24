import pathlib
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
path = "/Users/matt/Projects/msg-backend/tracks"
go_recursively = True
my_observer = Observer()
my_observer.schedule(my_event_handler, path, recursive=go_recursively)

currently_scanning = False

accepted_filetypes = ["mp3","wav","aif","flac"]

def on_created(event):
    print("Triggered on_created")

    if currently_scanning == False:
        # clear_db()
        print(f"hey, {event.src_path} has been created!")
        scanner()

def scanner():
    currently_scanning = True

    directory = os.fsencode(path)
    print("Path: " + path)

    for file in os.listdir(directory):
        file_name = os.fsdecode(file)
        headers = {'Content-Type': 'application/json'}

        r = requests.post("http://localhost:6001/api/check_if_exists", json={
            "fileName": file_name
        }, headers=headers)

        print("file_name",file_name)
        print("DOES EXIST RESULT",r.text)
        print("length", len(r.text))

        split_file_name = file_name.split(".")

        if split_file_name[len(split_file_name)-1] in accepted_filetypes:
            if len(r.text) <= 1:
                print("Analysing: " + file_name)

                full_name = path + "/" + file_name
                print("full_name: " + full_name) 

                try:
                    x, sr = librosa.load(full_name)
                except EOFError:
                    time.sleep(1)
                    print("End of file error in loading",file_name)
                    print("Restarting scanner")
                    clear_db()
                    scanner()
                    break
                except FileNotFoundError:
                    time.sleep(1)
                    print("File not found error in loading",file_name)
                    print("Restarting scanner")
                    clear_db()
                    scanner()
                    break         

                if x.all() != None:
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
                    contrast_mean = int(contrast[4][1])
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

                    r = requests.post("http://localhost:6001/api/da")
    
    print("Done!")
    # r = requests.post("http://localhost:6001/api/da")
    currently_scanning = False

def on_deleted(event):
    if currently_scanning == False:
        headers = {'Content-Type': 'application/json'}

        print(f"hey, {event.src_path} has been deleted!")

        split_file_name = event.src_path.split("/")
        removing_file = split_file_name[len(split_file_name)-1]

        print("Removing",removing_file)

        r = requests.post("http://localhost:6001/api/remove", json={
            "fileName": removing_file
        }, headers=headers)

        # file = pathlib.Path(event.src_path)

        # r = requests.post("http://localhost:6001/api/remove", json={
        #         "fileName": file.name
        #     }, headers=headers)
        
        # r = requests.post("http://localhost:6001/api/da")
        scanner()
        r = requests.post("http://localhost:6001/api/da")

def on_modified(event):
    # clear_db()
    print(f"hey, {event.src_path} has been modified!")
    # scanner()

def db_post(payload):
    print("Posting", payload)
    headers = {'Content-Type': 'application/json'}
    r = requests.post("http://localhost:6001/api/tracks", json=payload, headers=headers)
    # preflight, checks = cors.preflight.prepare_preflight(r)

    # print("Text", r.text)
    # print("Headers", r.headers)
    # print("Whole request",r)

    print("Post complete!")

def clear_db():
    r = requests.post("http://localhost:6001/api/cleartracks", json={})

    # print("Text", r.text)
    # print("Headers", r.headers)
    # print("Whole request",r)

    print("Clear database complete!")


my_event_handler.on_created = on_created
my_event_handler.on_deleted = on_deleted
# my_event_handler.on_modified = on_modified

clear_db()
r = requests.post("http://localhost:6001/api/da")

scanner()

r = requests.post("http://localhost:6001/api/da")
my_observer.start()

try:
    while True:
        time.sleep(1)
        # break
except KeyboardInterrupt:
    my_observer.stop()
    my_observer.join()
