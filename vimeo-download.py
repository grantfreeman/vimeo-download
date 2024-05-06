#!/usr/bin/env python3

import argparse
import base64
import csv
from enum import Enum, auto
import os
import pathlib
import re
import requests
import subprocess
from tqdm import tqdm
from tty_menu import tty_menu

class AudioQuality(Enum):
    """
    Vimeo audio quality options.

    Rates vary video to video.
    Use configure_quality(True) to see detailed options.
    """
    LOW = 0
    MED = 1
    HI  = 2

class VideoQuality(Enum):
    """
    Vimeo video quality options.

    The following choices are the standard resolutions.
    However, the source video may differ from what is visible on vimeo.
    For older videos, enable interactive fallback, configure_quality(True),
    to see detailed options.
    """
    V240  =  240 # 240p
    V360  =  360 # 360p
    V540  =  540 # 540p
    V720  =  720 # 720p
    V1080 = 1080 # 1080p
    V1440 = 1440 # 2K
    V2160 = 2160 # 4K
    VMAX  =    0 # select highest resolution available

class VimeoDownload():
    def __init__(self, output_file: str, master_json_url: str):
        self.output_file = output_file
        self.master_json_url = master_json_url
        self.master_json = None
        self.base_url = None
        self.audio_json = None
        self.video_json = None
        self.audio_file = None
        self.video_file = None

        # get master_json
        response = requests.get(self.master_json_url)
        if response.status_code == 410:
            print(f'ERROR: http code [{response.status_code}]. master.json expired, please update url and rerun.')
            response.raise_for_status()
        if response.status_code != 200:
            print(f'ERROR: received http code [{response.status_code}] when downloading master.json')
            response.raise_for_status()
        self.master_json = response.json()

        # generate base_url
        # master.json has a top level 'base_url' that is not used everytime
        # test multiple endpoints to determine correct url path
        slash = self.master_json_url.rfind('/')
        trimmed_url = self.master_json_url[:slash + 1]
        test_video = self.master_json['video'][0]
        response = requests.get(
            trimmed_url
            + self.master_json['base_url']
            + test_video['base_url']
            + test_video['segments'][0]['url'],
            stream=True
        )
        if response.status_code == 200:
            self.base_url = trimmed_url + self.master_json['base_url']
        else:
            self.base_url = trimmed_url
    
    def output_filename(self) -> str:
        return os.path.basename(self.output_file)
    
    def output_directory(self) -> str:
        return os.path.dirname(os.path.abspath(self.output_file))
    
    def list_widths(self):
        return [video['width'] for video in self.master_json['video']]

    def list_heights(self):
        return [video['height'] for video in self.master_json['video']]
    
    def list_sample_rates(self):
        return [audio['sample_rate'] for audio in self.master_json['audio']]
    
    def list_bitrates(self):
        return [audio['bitrate'] for audio in self.master_json['audio']]

    def _ask_audio_quality(self) -> int:
        """
        Returns: audio bitrate
        """
        # organize audio rates for menu
        samples = self.list_sample_rates()
        samples.sort(reverse=True)
        bitrates = self.list_bitrates()
        bitrates.sort(reverse=True)

        # create menu options
        rates = []
        for index in range(len(samples)):
            rates.append(f'{samples[index]}/{bitrates[index]}')
        index = tty_menu(rates, 'Audio Quality? (sample_rate/bitrate)')

        # selected audio bitrate
        return bitrates[index]

    def _ask_video_quality(self) -> int:
        """
        Returns: video height
        """
        # organize display resolutions for menu
        heights = self.list_heights()
        heights.sort(reverse=True)
        widths = self.list_widths()
        widths.sort(reverse=True)

        # create menu options
        resolutions = []
        for index in range(len(heights)):
            resolutions.append(f'{widths[index]}x{heights[index]}')
        index = tty_menu(resolutions, 'Video Quality? (width x height)')

        # selected video height
        return heights[index]
    
    def configure_quality(self, interactive_fallback: bool,
        audio_quality: VideoQuality = None,
        video_quality: AudioQuality = None
        ) -> None:
        """
        Configure the Quality 

        Parameters:
        interactive_fallback (bool): provides available qualities for a given 
            download for the user to select. This can be used as a default 
            setting or simply as a fallback if the specified video/audio is 
            not available.
        audio_quality (AudioQuality): desired audio quality
        video_quality (VideoQuality): desired video quality
        
        Returns: None

        Examples:
            # user picks audio and video
            download.configure_quality(True)

            # user options will display if desired options
            # are not available
            download.configure_quality(True, AudioQuality.LOW, VideoQuality.V720)
            
            # will throw an error if quality options are not present
            download.configure_quality(False, AudioQuality.MED, VideoQuality.V1440)
            
            # will always fail, must  provide audio and video args
            download.configure_quality(False, VideoQuality.VMAX)
        """
        if interactive_fallback == False and (audio_quality == None or video_quality == None):
            raise ValueError("Must provide audio and video quality when interactive == False")
        
        print(f'\n======== {self.output_filename()} ========')
        
        # Process audio quality
        if audio_quality == None:
            bitrate = self._ask_audio_quality()
        else:
            bitrates = self.list_bitrates()
            bitrates.sort() # sorts low to high
            if audio_quality == AudioQuality.HI:
                bitrate = bitrates[-1]
            else:
                bitrate = bitrates[audio_quality.value]
        
        # Set audio quality
        index = self.list_bitrates().index(bitrate)
        self.audio_json = self.master_json['audio'][index]
        
        # Process video quality
        if video_quality == None:
            height = self._ask_video_quality()
        elif video_quality == VideoQuality.VMAX:
            height = max(self.list_heights())
        elif video_quality.value in self.list_heights():
            height = video_quality.value
        else:
            # fuzzy search within 5% pixel range
            heights = self.list_heights()
            position = None
            for index, height in enumerate(heights):
                if (height * 0.95) <= video_quality.value <= (height * 1.05):
                    position = index
                    break
            if position != None:
                height = heights[position]
            
            # fuzzy search failed, ask user if interactive mode
            else:
                if interactive_fallback == True:
                    print(f'{video_quality.value}p is not available. See options below')
                    height = self._ask_video_quality()
                else:
                    raise ValueError(f'Unable to find video quality matching {video_quality.value}p')
        
        # Set video quality
        index = self.list_heights().index(height)
        self.video_json = self.master_json['video'][index]

        # configuration complete
        print('---- quality configuration ----')
        print(f'video\t{self.video_json['width']}x{self.video_json['height']}')
        print(f'audio\t{self.audio_json['sample_rate']}/{self.audio_json['bitrate']}')
    
    def download_audio_video(self):
        if self.audio_json == None or self.video_json == None:
            raise ValueError('Error: must configure_quality() before calling download_audio_video()')
        
        print(f'\n======== {self.output_filename()} ========')
        print(f'---- downloading audio and video ----')

        # create output path if it doesn't exist
        pathlib.Path(self.output_directory()).mkdir(parents=True, exist_ok=True)
        
        # download audio file
        audio_base_url = self.base_url + self.audio_json['base_url']
        name = os.path.splitext(self.output_filename())[0]
        self.audio_file = f'{self.output_directory()}/{name}_audio_{self.audio_json['id']}.m4a'
        audio_file = open(self.audio_file, 'wb')
        init_segment = base64.b64decode(self.audio_json['init_segment'])
        audio_file.write(init_segment)

        for segment in tqdm(self.audio_json['segments']):
            segment_url = audio_base_url + segment['url']
            # segment_url = re.sub(r'/[a-zA-Z0-9_-]*/\.\./',r'/',segment_url.rstrip())
            response = requests.get(segment_url, stream=True)
            if response.status_code != 200:
                print(f'ERROR: received http code [{response.status_code}] when downloading audio')
                response.raise_for_status()
            for chunk in response:
                audio_file.write(chunk)

        audio_file.flush()
        audio_file.close()

        # create video file
        video_base_url = self.base_url + self.video_json['base_url']
        self.video_file = f'{self.output_directory()}/{name}_video_{self.video_json['id']}.mp4'
        video_file = open(self.video_file, 'wb')
        init_segment = base64.b64decode(self.video_json['init_segment'])
        video_file.write(init_segment)

        for segment in tqdm(self.video_json['segments']):
            segment_url = video_base_url + segment['url']
            response = requests.get(segment_url, stream=True)
            if response.status_code != 200:
                print(f'ERROR: received http code [{response.status_code}] when downloading video')
                response.raise_for_status()
            for chunk in response:
                video_file.write(chunk)

        # video cleanup
        video_file.flush()
        video_file.close()
    
    def combine_audio_video(self):
        if self.audio_file == None or self.video_file == None:
            raise ValueError('Error: must download_audio_video() before calling combine_audio_video()')
        if not os.path.exists(self.audio_file) or not os.path.exists(self.video_file):
            raise ValueError('Error: unable to find specified audio and video files to be combined.')
        
        print(f'\n======== {self.output_filename()} ========')
        print(f'---- combining audio and video ----')

        # combine using ffmpeg
        command = f'ffmpeg -v quiet -stats -y -i "{self.audio_file}" -i "{self.video_file}" "{self.output_file}"'
        subprocess.call(command, shell=True)

        # delete stream files
        os.remove(self.audio_file)
        os.remove(self.video_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='Vimeo Downloader',
        description='vimeo download automation tool'
    )
    parser.add_argument(
        'tsv_file',
        type=argparse.FileType('r', encoding='UTF-8'),
        help='tab-separated values file containing vimeo download requests')
    
    # parse tsv file
    args = parser.parse_args()
    tsv_file = csv.reader(args.tsv_file, delimiter="\t")
    request_list = []
    for video, audio, output, url in tsv_file:
        download = VimeoDownload(output, url)
        video_quality = VideoQuality[video] if video else None
        audio_quality = AudioQuality[audio] if audio else None
        download.configure_quality(True, audio_quality, video_quality)
        request_list.append(download)
    args.tsv_file.close()

    # prioritize downloading audio video in case endpoints expire
    for download in request_list:
        download.download_audio_video()
    
    # combine audio video
    for download in request_list:
        download.combine_audio_video()