"""
Yash Music Downloader | CS Summative
CLI tool that lets users upload YouTube URLs and download M4A audio files
ICS3U
Yash Trivedi
2026-06-01

REQUIRED PACKAGE INSTALLS: pytubefix, mutagen, opencv-python, python3-discogs-client, python-dotenv, requests, questionary
"""

# TO RUN IN THONNY, HOVER OVER RUN > RUN CURRENT SCRIPT IN TERMINAL

### IMPORTS ###

from pytubefix import YouTube
from pytubefix.cli import on_progress
from pytubefix import Playlist

from mutagen.mp4 import MP4
from mutagen.mp4 import MP4Cover

import os

import urllib.request

import cv2

import tkinter as tk
from tkinter import filedialog

import discogs_client

from dotenv import load_dotenv

import requests

import questionary
from questionary import Choice


load_dotenv() # YouTube videos said that this is very important to run at the start of my program so that it can properly pull the token from the other file

### CONSTANTS ###

# The weird \xa strings are how mutagen tags in python
STRING_TAGS = {
    "Track title" : ["\xa9nam", "title"],  # track title
    "Album name" : ["\xa9alb", "album"], # album
    "Artist" : ["\xa9ART", "artist"], # artist
    "Album artist" : ["aART", "album artist"], # album artist? does it work? test it
    "Release year" : ["\xa9day", "year"], # year
    "Genre" : ["\xa9gen", "genre"], # genre
    }


HEADERS = {'Authorization': f'Discogs token={os.getenv("TOKEN")}',
           'User-Agent': 'yashskl_mp3_tag_edititor/1.0'} # so that requests doesnt get blocked when downloading from discogs returned urls


CLIENT = discogs_client.Client('yashskl_mp3_tag_edititor/1.0', user_token=os.getenv('TOKEN'))

### FUNCTIONS ###

def autofill_metadata(audio, track, artist, year):
    """
    Uses Discogs API and text pulled from a YouTube to attempt to find a matching song and append more metadata to the audio file. Results vary. 

    Parameters: 
        audio - MP4 object of a file path, 
        track - YouTube video title (str), 
        artist - video channel name (str), 
        year - video upload year (int)
    """
    releases = CLIENT.search(f"{track} {year}", artist=artist, type='master') # Searches API using CLIENT originally initialized

    if len(releases) == 0: # If no releases are found, a more vague description is used to turn up something
        releases = CLIENT.search(f"{track}", artist=artist, type='master') 

    if len(releases) == 0:
        releases = CLIENT.search(f"{track}", type='master')

    if len(releases) == 0:
        print("Sorry, no recorded metadata of the mentioned song was found through Discogs API.")
        

    else: # When release is found
            
        release = releases[0] # Releases is like a list of albums, so release is like the first album

        album = release.title.split(' - ')[-1] # this is because the string is originally returned as "artist - album"
        new_artist = release.title.split(' - ')[0] # if video was an unofficial upload
        genre = (release.genres)[0] # returns list, so just take first item of list and set that to genre
        total = len(release.tracklist) 

        position = None
        i = 0

        for t in release.tracklist:
            i+=1
            if t.title.lower() == track.lower(): # in case of incorrect capitalization from unofficial upload
                position = i
                audio["trkn"] = [(position, total)]
                audio.save()
                break

        image_url = releases[0].images[0]['uri']  # full size, you can add 150 to get the 150x150 image

        response = requests.get(image_url, headers=HEADERS) # Using requests instead of urllib because authentication is easier

        with open("discogs_icon.jpg", "wb") as f: # wb is write binary - creates new file or overwrites if it already exists. 
            f.write(response.content) # writes the binary pulled from the image from Discogs

        icon(audio, "discogs_icon.jpg")
        os.remove("discogs_icon.jpg")
        
        audio["\xa9alb"] = [album]
        audio["\xa9ART"] = [new_artist]
        audio["\xa9gen"] = [genre]
        

        audio.save()
        


def string_edit(choice, audio, string, file_path): 
    """
    Many metadata tags are just strings that need to be edited, so I made a function for all metadata strings
    Parameters: 
        choice - what attribute is being editied (str), 
        audio - MP4 mutagen object, string - what the attribute will be written as (str), 
        file_path - audio's file path (str)
    """
    audio[(STRING_TAGS[choice])[0]] = [string]
    audio.save()
    if choice == "Track title":
        path_before_name = os.path.dirname(file_path)
        new_path = path_before_name + "/" + string + ".m4a"
        os.rename(file_path, new_path)
    

def track_number_edit(audio, number, total):
    """
    Edits track number or position of a file
    Parameters: 
        audio - MP4 object (what's being edited), 
        number - position of track in album (int), 
        total - total number of tracks on album (int)
    """
    audio["trkn"] = [(number, total)]
    audio.save()


def icon(audio, img):
    """
    Changes the track cover of a file
    Parameters: 
        audio - MP4 object (song), 
        img - selected image's file path (str)
    """
    with open(img, "rb") as f:
        cover_data = f.read()
        audio["covr"] = [MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)]
        audio.save()


def square_icon(yt, audio):
    """
    Downloads thumbnail from YouTube, crops it to be a square, and adds it to file
    Parameters: 
        yt - the YouTube video object form PyTubeFix, 
        audio - MP4 mutagen object song
    """
    url = yt.thumbnail_url
    urllib.request.urlretrieve(url, "temp_thumb.jpg")
     
    img = cv2.imread("temp_thumb.jpg")
    height = img.shape[0]
    width = img.shape[1]
        

    # OpenCV is used to crop, it uses x and y and start and end. Each image is 640 x 480
    x_start = int((width * (7/16)) / 2)
    x_end = int(width - x_start)
    y_start = int(height*((1/4)/2))
    y_end = int(height - (y_start))
    cropped_img = img[y_start:y_end, x_start:x_end]
    cv2.imwrite("finalthumb.jpg", cropped_img)
    os.remove("temp_thumb.jpg")
            
    with open("finalthumb.jpg", "rb") as f:
        cover_data = f.read()
        audio["covr"] = [MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)]
        audio.save()
             
    os.remove("finalthumb.jpg")
    

def default_icon(yt, audio):
    """
    Gets the original thumbnail and just sets that as the file cover
    Parameters: 
        yt - YouTube object from PyTubeFix so you can get title and thumbnail and stuff, 
        audio - mutagen MP4 object
    """
    url = yt.thumbnail_url
    urllib.request.urlretrieve(url, "temp_thumb.jpg")
    
    with open("temp_thumb.jpg", "rb") as f:
        cover_data = f.read()
        audio["covr"] = [MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)]
        audio.save()
            
    os.remove("temp_thumb.jpg")


def download_process(yt, select_crop, crop_preset, metadata_preset, output_folder):
    """
    Actual downloading. It's been put into a sperate function from download so that you can spam this one function for bulk downloads
    Parameters: 
        yt - YouTube object from PyTubeFix, 
        select_crop - whether or not it asks the user if the thumbnail is square or not, 
        crop_preset - if not it refers to this variable to automatically crop it or not, 
        metadata_preset - whether or not metdata is applied, 
        output_folder - the folder where the downloaded audio is stored
    """
    artist = yt.author
    if artist[-8:] == " - Topic": # Many artists without a channel have their song under a Topic channel. This prevents that from coming into the metadata
        artist = artist[0:-8]
            
    print(yt.title)
     
    ys = yt.streams.get_audio_only()


    ys.download(output_path = output_folder)
            

    file_name = yt.title + ".m4a"


    # special characters that get removed from the file name when downloading. created many many problems for me while testing.
    for c in ['"', '*', '/', '?', '|', ':', '\\', '<', '>']: # double backslash should be interpreted as one backslash
        file_name = file_name.replace(c, '')
    
    full_path = output_folder + "/" + file_name

    audio = MP4(full_path)
        
    audio["\xa9nam"] = [yt.title]
    audio["\xa9ART"] = [artist]
    audio["\xa9day"] = [str(yt.publish_date.year)]
        
    if select_crop:
        square_cover = questionary.confirm("Is the thumbnail a proper square album cover?").ask()
                
        if square_cover:
            square_icon(yt, audio)
                
        else:
            default_icon(yt, audio)
        
    else:
        if crop_preset == "Square":
            square_icon(yt, audio)
            
        else:
            default_icon(yt, audio)

    audio.save()

    if metadata_preset:
        autofill_metadata(audio, yt.title, artist, str(yt.publish_date.year))
    else:
        pass
    
    


def download(): 
    """
    Starting download process, figures out whether a single video or a whole playlist is being downloaded
    """
    url = input("Enter URL for song / playlist: ")
    valid_url = False
    while not valid_url:
        try:
            if 'list' in url: # playlists have the word list in their url, so I check that here
                Playlist(url)
            else:
                YouTube(url)
            valid_url = True
        except Exception:
            print("URL doesn't seem to be valid... Please verify you have the correct URL or try another.")
            url = input("Enter URL for song/playlist: ")

    print("Please select desired output folder...")
    output_folder_path = gfp_folder()

    while output_folder_path == "":
        print("Please select desired output folder...")
        output_folder_path = gfp_folder()


    if not 'list' in url:
        yt = YouTube(url, on_progress_callback=on_progress)
        
        download_process(yt, settings_dict["icon"], settings_dict["icon_preset"], settings_dict["metadata"], output_folder_path)
        

    else:
        pl = Playlist(url)
        

        for yt in pl.videos:
            download_process(yt, settings_dict["icon"], settings_dict["icon_preset"], settings_dict["metadata"], output_folder_path)
            
    
    input("\n\nDownloaded!")
    
    will_continue = questionary.confirm("Would you like to keep downloading/editing?").ask()
    return will_continue
    
    
def gfp_song(): # get file path
    """
    Gets the file path for songs for editing
    Returns: File path (str)
    """
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    file_paths = filedialog.askopenfilenames(
        title="Select  files",
        filetypes=[("M4A", "*.m4a")]
    )
    
    root.destroy()
    
    return file_paths


def gfp_cover():
    """
    Gets the image file paths for editiing song covers
    Returns: File path (str)
    """
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    file_path = filedialog.askopenfilename(
        title="Select a file",
        filetypes=[("Image files", "*.png *.jpg *.jpeg *.JPG *.JPEG *.PNG")]
    )
    
    root.destroy()
    
    return file_path


def gfp_folder():
    """
    Gets the folder path for output path designation
    Returns: File path (str)
    """
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    
    folder_path = filedialog.askdirectory(
        title="Select a folder",
    )
    
    root.destroy()
    
    return folder_path


def edit():
    """
    Allows users to edit one song or multiple. Different options for metadata to edit depending on whether it's one song or many. Multiple songs also have bulk and manual editing.
    """
    input("Select the audio files you'd like to edit: ")
    files = gfp_song()

    while len(files) == 0:
        input("Select the audio files you'd like to edit: ")
        files = gfp_song()

    if len(files) == 1:
        choice = questionary.select("What attribute would you like to edit?", choices = ["Track title", "Album name", "Track cover", "Artist", "Album artist", "Release year", "Track number/position", "Genre"]).ask()

        audio = MP4(files[0])

        if choice in STRING_TAGS.keys():
            string = input(f"Enter {STRING_TAGS[choice][1]}: ")
            string_edit(choice, audio, string, files[0])
            
        elif choice == 'Track number/position':
            number = int(input("Enter track number: "))
            total = int(input("Enter total number of tracks in album: "))

            while total < number:
                print("Please make sure the total number of tracks is greater than the track number.")
                number = int(input("Enter track number: "))
                total = int(input("Enter total number of tracks in album: "))

            track_number_edit(audio, number, total)

#         elif choice == 'Track cover':
        else:
            input("Enter image icon: ")
            icon_path = gfp_cover()

            while icon_path == "":
                print("Please enter desired icon")
                icon_path = gfp_cover()
            icon(audio, icon_path)

        
    else: 

        manual_or_bulk = questionary.select("How would you like to edit?", choices=["Manual", "Bulk", "Enumerate album"]).ask()

        if manual_or_bulk == 'Bulk':

            choice = questionary.select("What attribute would you like to edit?", choices = ["Album name", "Track cover", "Artist", "Album artist", "Release year", "Track number/position", "Genre"]).ask()
            
            if choice in STRING_TAGS.keys():
                string = input(f"Enter {STRING_TAGS[choice][1]}: ")

            elif choice == 'Track number/position':
                number = int(input("Enter track number: "))
                total = int(input("Enter total number of tracks in album: "))

                while total < number:
                    print("Please make sure the total number of tracks is greater than the track number.")
                    number = int(input("Enter track number: "))
                    total = int(input("Enter total number of tracks in album: "))

#             elif choice == 'Track cover':
            else:
                input("Enter image icon: ")
                icon_path = gfp_cover()
            
            
            for file in files:
                audio = MP4(file)
                if choice in STRING_TAGS.keys():
                    string_edit(choice, audio, string, file)
                elif choice == 'Track number/position':
                    track_number_edit(audio, number, total)
                elif choice == 'Track cover':
                    icon(audio, icon_path)


        elif manual_or_bulk == 'Manual':
            choice = questionary.select("What attribute would you like to edit?", choices = ["Track title", "Album name", "Track cover", "Artist", "Album artist", "Release year", "Track number/position", "Genre"]).ask()

            for file in files:
                audio = MP4(file)
                song_name = audio['\xa9nam'] # Put in seperate vairable cuz of f string complications

                if choice in STRING_TAGS.keys():
                    string = input(f"Enter {(STRING_TAGS[choice])[1]} for {song_name}: ")
                    string_edit(choice, audio, string, file)

                elif choice == 'Track number/position':
                    number = int(input(f"Enter {song_name}'s track number: "))
                    total = int(input("Enter the total number of tracks on the album: "))

                    while total < number:
                        print("Please make sure the total number of tracks is greater than the track number.")
                        number = int(input("Enter track number: "))
                        total = int(input("Enter total number of tracks in album: "))
                        
                    track_number_edit(audio, number, total)
                
#                 elif choice == 'Track cover':
                else:
                    input(f"Input {song_name}'s image: ")
                    icon_path = gfp_cover()
                    icon(audio, icon_path)
                    
        else:
            print("This is for songs in the same album. Please select the songs in the correct order as well.")
            total = len(files)
            i=0
            
            for file in files:
                i+=1
                audio = MP4(file)
                track_number_edit(audio, i, total)
                
                    
    input("Changes saved!")
    
    will_continue = questionary.confirm("Would you like to keep downloading/editing?").ask()
    return will_continue
        
                
def settings():
    """
    Settings to reduce the amount of questions asked throughout the program. Everything is put in a dictionary to refer to later. 
    """

    settings_questions = questionary.checkbox("Settings", choices=[Choice("When downloading, ask how thumbnail should be cropped (square or raw)", checked=settings_dict["icon"]), Choice("Automatically apply Discogs metadata", checked=settings_dict["metadata"])]).ask()

    icon_decision = "When downloading, ask how thumbnail should be cropped (square or raw)" in settings_questions 
    metadata_decision = "Automatically apply Discogs metadata" in settings_questions

    icon_preset = None

    if icon_decision == False:
        icon_preset = questionary.select("If you are not prompted, how should the icon be cropped?", choices=["Square", "Raw"]).ask()


    settings_dict["icon"] = icon_decision
    settings_dict["metadata"] = metadata_decision
    settings_dict["icon_preset"] = icon_preset
    
    return True


def menu():
    """
    Start menu. Is called to "restart" the program. 
    """
    
    restart_menu = True

    while restart_menu:
        edit_or_download = questionary.select(
            "What do you want to do?",
            choices=["Download", "Edit", "Settings", "Exit"],
        ).ask()
        
        if edit_or_download == 'Edit':
            restart_menu = edit()
            
        elif edit_or_download == 'Download':
            restart_menu = download()

        elif edit_or_download == 'Settings':
            restart_menu = settings()
        else:
            restart_menu = False
            
### MAIN ###
            
settings_dict = { # Dictionary with settings for later use
    "icon" : True, # Should you be prompted to crop or not crop thumbnails?
    "metadata" : True, # Should metadata be automatically added from Discogs?
    "icon_preset" : None # If you aren'y prompted, what's the default ratio for the thumbnail -> to be put as M4A cover
}

# Introduction

print("""
Welcome to Yash's Music Downloader!!!!
I download a lot of music and have some peeves with current online downloaders, so I created a CLI tool that fixes those issues, escpecially with bulk downloading and editing.
Some YouTube videos won't be recogonized on school internet, but everything seems to work fine on normal Wi-Fi.
All data and images come from YouTube through PyTubeFix, or from Discogs through their API.
Please enjoy, but totally don't download copyrighted music and do illegal stuff cuz that's bad and illegal :p
Copyrighted music is owned by the musicians and you do NOT have the right to handle and distribute their music by using this program.
All files are in M4A format, not MP3. But basically all softare that handles MP3 files handles MP4 ones the same.
ALSO: When asked a Y/n question, just click the letter key... no need to click enter!
""")

menu()