import pathlib
from shutil import ignore_patterns
import numpy
import librosa
import os

import json
import numpy as np

import requests

import time
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

import math
import sklearn.metrics
import pandas as pd
from scipy.spatial.distance import pdist,squareform

from websocket import create_connection

import pickle

ws = create_connection("ws://localhost:9000")

# import keyboard

# from pydub import AudioSegment

if __name__ == "__main__":  # pattern matcher
    patterns = ["*"]
    ignore_patterns = None
    ignore_directories = True
    case_sensitive = False
    my_event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)

# Setting values for the observer

# path = "/Users/matt/Projects/msg-backend/tracks"
path = "./tracks"

s1 = []
s2 = []
avgs = []

current_tracks = []

current_comparisons = np.array([])

current_task = "NONE"
current_comp = ""
total_task_amt = 0
total_task_done = 0

go_recursively = True
my_observer = Observer()
my_observer.schedule(my_event_handler, path, recursive=go_recursively)

currently_scanning = False

accepted_filetypes = ["mp3","wav","aif","flac", "aiff","m4a"]

def round_to_nearest(n, s):
    return np.round(n,decimals = s)

def post_status():
    headers = {'Content-Type': 'application/json'}

    status_string = "STATUS?" + current_task + ": " + str(total_task_done) + " / " + str(total_task_amt) + " (" + current_comp + ")"

    # print("SENDING",status_string)

    r = requests.post("http://localhost:6001/api/send_status_text", json={
            "statusText": status_string
        }, headers=headers)

def on_created(event):
    print("Triggered on_created")

    if currently_scanning == False:
        current_tracks = []
        clear_similarities_db()
        # clear_db()
        print(f"[TRACK] hey, {event.src_path} has been created!")
        scanner()

def scanner():
    r = requests.post("http://localhost:6001/api/lock")

    # current_tracks = []
    global current_comp
    global current_tracks
    global current_task
    global total_task_done
    global total_task_amt

    current_comp = "..."

    directory = os.fsencode(path)
    print("Path: " + path)

    incr = 0

    current_task = "SCANNING"
    total_task_amt = 0
    total_task_done = 0
    post_status()

    for file in os.listdir(directory):
        total_task_amt = total_task_amt + 1

    for file in os.listdir(directory):
        print("FILE FOUND")
        file_name = os.fsdecode(file)
        headers = {'Content-Type': 'application/json'}

        r = requests.post("http://localhost:6001/api/check_if_exists", json={
            "fileName": file_name
        }, headers=headers)

        print("[TRACK] file_name",file_name)
        print("[TRACK] DOES EXIST RESULT",r.text)
        print("[TRACK] length", len(r.text))

        split_file_name = file_name.split(".")
        print(split_file_name)

        if split_file_name[len(split_file_name)-1] in accepted_filetypes:
            # print("doing")
            if len(r.text) == len(r.text):
                # print("DOING IT!")
                print("[TRACK] Analysing: " + file_name)

                full_name = path + "/" + file_name
                print("[TRACK] full_name: " + full_name) 

                try:
                    x, sr = librosa.load(full_name)
                except EOFError:
                    time.sleep(1)
                    print("[TRACK] End of file error in loading",file_name)
                    print("[TRACK] Restarting scanner")
                    clear_tracks_db()
                    scanner()
                    break
                except FileNotFoundError:
                    time.sleep(1)
                    print("[TRACK] File not found error in loading",file_name)
                    print("[TRACK] Restarting scanner")
                    clear_tracks_db()
                    scanner()
                    break         

                if x.all() != None:
                    tempo = librosa.beat.tempo(x, sr=sr)

                    genre = ""

                    contrast = librosa.feature.spectral_contrast(x, sr=sr)
                    chroma_stft = librosa.feature.chroma_stft(x, sr=sr)
                    rmse = librosa.feature.rms(x)
                    spec_cent = librosa.feature.spectral_centroid(x, sr=sr)
                    spec_bw = librosa.feature.spectral_bandwidth(x, sr=sr)
                    rolloff = librosa.feature.spectral_rolloff(x, sr=sr)
                    zcr = librosa.feature.zero_crossing_rate(x)
                    mfcc = librosa.feature.mfcc(x, sr=sr)

                    n_f_name = str(incr) + ".npy"
                    np.save("./explo/"+n_f_name, contrast)

                    adj_tempo = int(tempo[0])

                    working_tr = {
                        "fileName": file_name,
                        "chroma_stft": chroma_stft,
                        "genre": genre,
                        "tempo": adj_tempo,
                        "rmse": rmse,
                        "contrast": contrast,
                        "centroid": spec_cent,
                        "bandwidth": spec_bw,
                        "zcr": zcr,
                        "mfcc": mfcc,
                        "rolloff": rolloff,
                    }

                    print(working_tr)

                    chroma_stft_mean = int(numpy.mean(chroma_stft))
                    contrast_mean = int(contrast[4][1])
                    rmse_mean = int(numpy.mean(rmse))
                    spec_cent_mean = int(numpy.mean(spec_cent))
                    spec_bw_mean = int(numpy.mean(spec_bw))
                    rolloff_mean = int(numpy.mean(rolloff))
                    zcr_mean = int(numpy.mean(zcr))

                    db_post_track({
                        "fileName": file_name,
                        "genre": genre,
                        "tempo": adj_tempo,
                        "rmse": rmse_mean,
                        "contrast": contrast_mean,
                        "centroid": spec_cent_mean,
                        "bandwidth": spec_bw_mean,
                        "rolloff": rolloff_mean,
                    })
                    current_tracks.append(working_tr)

                    total_task_done = total_task_done + 1
                    post_status()

                    # print('[SIMILARITY] Creating track similarities for track with index',incr)
                    # create_similarity_matrix(incr, mode="each")

                    incr = incr + 1

                    # current_tracks.append({
                    #         "fileName": file_name,
                    #         "genre": genre,
                    #         "tempo": adj_tempo,
                    #         "rmse": rmse_mean,
                    #         "contrast": contrast_mean,
                    #         "centroid": spec_cent_mean,
                    #         "bandwidth": spec_bw_mean,
                    #         "rolloff": rolloff_mean,
                    # })

                    r = requests.post("http://localhost:6001/api/da")
    
    print("Done!")

    create_similarity_matrix(mode="all")
    r = requests.post("http://localhost:6001/api/da")

    currently_scanning = False
    current_task = "DONE"
    post_status()

    r = requests.post("http://localhost:6001/api/unlock")

def on_deleted(event):
    if currently_scanning == False:
        current_tracks = []
        clear_similarities_db()
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

def db_post_track(payload):
    print("[TRACK] Posting", payload)
    headers = {'Content-Type': 'application/json'}
    r = requests.post("http://localhost:6001/api/tracks", json=payload, headers=headers)
    # preflight, checks = cors.preflight.prepare_preflight(r)

    # print("[TRACK] Text", r.text)
    # print("[TRACK] Headers", r.headers)
    # print("[TRACK] Whole request",r)

    print("[TRACK] Post complete!")

def db_post_similarity(payload):
    print("[SIMILARITY] Posting", payload)
    headers = {'Content-Type': 'application/json'}
    r = requests.post("http://localhost:6001/api/similarities", json=payload, headers=headers)
    # preflight, checks = cors.preflight.prepare_preflight(r)

    # print("[SIMILARITY] Text", r.text)
    # print("[SIMILARITY] Headers", r.headers)
    # print("[SIMILARITY] Whole request",r)

    print("[SIMILARITY] Post complete!")

def clear_tracks_db():
    r = requests.post("http://localhost:6001/api/clear_tracks", json={})

    # print("Text", r.text)
    # print("Headers", r.headers)
    # print("Whole request",r)

    print("[TRACK] Clear database complete!")

def clear_similarities_db():
    r = requests.post("http://localhost:6001/api/clear_similarities", json={})

    # print("Text", r.text)
    # print("Headers", r.headers)
    # print("Whole request",r)

    print("[SIMILARITY] Clear database complete!")

def round_down_nearest_ten(input):
    return math.floor(input/10) * 10

def create_similarity_matrix(iter_val="off", mode="each"):

    global current_tracks
    global current_task
    global total_task_done
    global total_task_amt
    global current_comp

    current_task = "COMPARING"
    total_task_done = 0

    current_comparisons = []

    # # get track count
    # r = requests.get("http://localhost:6001/api/get_tracks_count")
    # r.raise_for_status()
    # track_count_response = r.json()
    # track_count = track_count_response["track_count"]
    # # print("[SIMILARITY] track_count", track_count)

    track_count = len(current_tracks)

    tracks_r_loc = current_tracks

    # retrive tracks after processing in db
    tracks_r = requests.get("http://localhost:6001/api/tracks")
    tracks_r.raise_for_status()
    tracks_r_db = tracks_r.json()
    # print("[SIMILARITY] tracks_r_response", tracks_r_response)

    print('[SIMILARITY] CURRENT TRACKS FROM API',tracks_r_db)

    global s2
    global s1
    global avgs
    global x_frame
    # global current_tracks

    x_frame = []

    # f = open('settings.json')

    # comparisons_to_make = json.load(f)

    # create similarity comparison

    settings_r = requests.get("http://localhost:6001/api/settings")
    settings_r.raise_for_status()
    settings_r_response = settings_r.json()

    print("[SETTINGS] settings_r_response", settings_r_response[0])

    comparisons_to_make = [
        {
            "type": "centroid",
            "tolerance": -1,
            "sim": settings_r_response[0]["centroidSim"],
            "colour": "#DE3C1A"
        },
        {
            "type": "contrast",
            "tolerance": -1,
            "sim": settings_r_response[0]["contrastSim"],
            "colour": "#D5DE14"
        },
        {
            "type": "bandwidth",
            "tolerance": -1,
            "sim": settings_r_response[0]["bandwidthSim"],
            "colour": "#36BB2D"
        },
        {
            "type": "rolloff",
            "tolerance": -2,
            "sim": settings_r_response[0]["rolloffSim"],
            "colour": "#14DED2"
        },
        {
            "type": "tempo",
            "tolerance": 0,
            "colour": "#DE14CF"
        },
        {
            "type": "rmse",
            "tolerance": -1,
            "sim": settings_r_response[0]["rmseSim"],
            "colour": "#957A84"
        },
        {
            "type": "zcr",
            "tolerance": -2,
            "sim": settings_r_response[0]["zcrSim"],
            "colour": "#257852"
        },
        {
            "type": "mfcc",
            "tolerance": -1,
            "sim": settings_r_response[0]["mfccSim"],
            "colour": "#D8A944"
        },
        {
            "type": "chroma_stft",
            "tolerance": -2,
            "sim": settings_r_response[0]["chromaStftSim"],
            "colour": "#8344D8"
        },
    ]

    ## comparison logic
    # print("[SIMILARITY] Starting comparison logic...")

    if iter_val != "off":
        if mode == "each":
            s_loop = range(iter_val)
        elif mode == "all":
            s_loop = range(track_count)
    else:
        s_loop = range(track_count)

    # Find total amount of tasks to do
    total_task_amt = 1
    for n in comparisons_to_make:
        for idx, i in enumerate(s_loop):
            for j in range(track_count):
                for x in current_comparisons:
                    print("[SIMILARITY] INCREMENTING TOTAL TASKS TO",total_task_amt)
                    total_task_amt = total_task_amt + 1

    # Do the tasks
    for n in comparisons_to_make:
        s1 = []
        for idx, i in enumerate(s_loop):
            s2 = []
            avgs = []
            for j in range(track_count):
                breaking = False

                for x in current_comparisons:
                    if ((x['target'] == tracks_r_db[i]["_id"]) & (x['source'] == tracks_r_db[j]["_id"])):
                        print("[SIMILARITY] Similarity already exists in reverse, skipping...")
                        total_task_done = total_task_done + 1
                        post_status()
                        breaking = True

                if breaking == True:
                    continue
                
                if(tracks_r_db[i] == tracks_r_db[j]):
                    print("SAME")
                else:
                    comp = n['type']
                    rounding_decimals = n['tolerance']

                    similarity_score_a = 0
                    similarity_score_b = 0

                    start = 0
                    dista = 9
                    leng = start+dista

                    # print("fff",tracks_r_response[i][comp].shape)

                    if comp == "tempo":
                        if round_to_nearest(tracks_r_loc[i][comp],n["tolerance"]) == round_to_nearest(tracks_r_loc[j][comp],n["tolerance"]):
                            print("[SIMILARITY]",comp,"match")

                            composed_similarity = {
                                "id": "'" + comp + "'" +  " " + "'" + tracks_r_db[i]["fileName"] + "'" +  " " + "'" + tracks_r_db[j]["fileName"] + "'",
                                "source": tracks_r_db[i]["_id"],
                                "target": tracks_r_db[j]["_id"],
                                "label": comp,
                                "colour": n['colour']
                            }

                            db_post_similarity(composed_similarity)
                            current_comparisons.append(composed_similarity)
                    else:
                        if isinstance(tracks_r_loc[i][comp], int):
                            print("[SIMILARITY]",comp,"is int")
                            x_frame = [0]
                        else:
                            i_arr = tracks_r_loc[i][comp][0:7,start:leng]
                            j_arr = tracks_r_loc[j][comp][0:7,start:leng]

                            i_arr_new = np.interp(i_arr, (i_arr.min(), i_arr.max()), (1, 10))
                            j_arr_new = np.interp(j_arr, (j_arr.min(), j_arr.max()), (1, 10))

                            # print("i_arr",i_arr)
                            # print("j_arr",j_arr)
                            
                            n_frame = np.zeros((7,dista), dtype=int)
                            # print("[SIMILARITY] frame shape", n_frame.shape)

                            for xdx, x in enumerate(i_arr_new):
                                for ydx, y in enumerate(x):
                                    # print("ydx",ydx)
                                    n_frame[xdx][ydx] = round_to_nearest(y,n["tolerance"])
                                    # total_task_done = total_task_done + 1
                                    # post_status()

                            for xdx, x in enumerate(j_arr_new):
                                for ydx, y in enumerate(x):
                                    if n_frame[xdx][ydx] != round_to_nearest(y,n["tolerance"]):
                                        n_frame[xdx][ydx] = round_to_nearest(y,n["tolerance"])
                                        # total_task_done = total_task_done + 1
                                        # post_status()

                            current_comp = comp
                            total_task_done = total_task_done + 1
                            post_status()

                            dist = numpy.linalg.norm(j_arr_new-i_arr_new)
                            # print("[SIMILARITY] dist",dist)

                            # print("[SIMILARITY] n_frame",n_frame)

                            s_dist = sklearn.metrics.pairwise.euclidean_distances(j_arr_new, i_arr_new)
                            s_dist_avg = np.average(s_dist)
                            # print("[SIMILARITY] s_dist_avg",s_dist_avg)

                            sqrt_s_dist_avg = math.sqrt(s_dist_avg)
                            avgs.append(s_dist_avg)
                            # print("[SIMILARITY] sqrt_s_dist_avg",sqrt_s_dist_avg)

                            x_frame = n_frame.tolist()

                            if(sqrt_s_dist_avg <= int(n["sim"])):
                                print("[SIMILARITY] is", sqrt_s_dist_avg)
                                print("[SIMILARITY]",comp,"match")

                                composed_similarity = {
                                    "id": "'" + comp + "'" +  " " + "'" + tracks_r_db[i]["fileName"] + "'" +  " " + "'" + tracks_r_db[j]["fileName"] + "'",
                                    "source": tracks_r_db[i]["_id"],
                                    "target": tracks_r_db[j]["_id"],
                                    "label": comp,
                                    "colour": n['colour']
                                }

                                db_post_similarity(composed_similarity)
                                current_comparisons.append(composed_similarity)
                                r = requests.post("http://localhost:6001/api/da")
                            # print("[SIMILARITY] avgs for",current_tracks[i]["fileName"],"and",current_tracks[j]["fileName"],comp,"are",avgs)

            total_task_done = total_task_done + 1
            if total_task_done > total_task_amt:
                total_task_amt = total_task_done
            post_status()

            s2.append([x_frame])
            print("[SIMILARITY] s2...")
        if (s2 != None) | (s2 != []):
            s1.append(s2)
            # total_task_done = total_task_done + 1
            # post_status()
        # print("[SIMILARITY] s1...")
    current_comparisons.append(s1)
    # print("[SIMILARITY] curr...")

    current_comp = ""

    print("[SIMILARITY] Finished comparison logic: mode",mode,"and iter_val",iter_val)
    current_tracks = []
    # print(current_comparisons)

my_event_handler.on_created = on_created
my_event_handler.on_deleted = on_deleted
# my_event_handler.on_modified = on_modified

clear_similarities_db()
clear_tracks_db()
r = requests.post("http://localhost:6001/api/da")

scanner()

r = requests.post("http://localhost:6001/api/da")
my_observer.start()

try:
    while True:
        result =  ws.recv()
        print("WS",result)
        if ((result == "SETTINGS") & (current_task == "DONE")):
            clear_similarities_db()
            current_comparisons = np.empty([])
            create_similarity_matrix(mode="all")

        inputString = input(':')

        if inputString == 'q':
            quit()

        if inputString == 's':
            clear_similarities_db()
            current_comparisons = np.empty([])
            create_similarity_matrix(mode="all")

        if inputString == 'r':
            clear_similarities_db()
            clear_tracks_db()
            r = requests.post("http://localhost:6001/api/da")

            scanner()

            r = requests.post("http://localhost:6001/api/da")
            # my_observer.start()
        # time.sleep(1)
        # break
        # break
except KeyboardInterrupt:
    my_observer.stop()
    my_observer.join()
