# vimeo-download
vimeo downloader tool

## Install (ubuntu)

Install Python 3 and ffmpeg:  
```bash
sudo apt install ffmpeg python3.12-venv python3.12-dev
```

Install Python modules:  
```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

## Video Download

1. create a tsv file with videos you want to download
2. run script with given tsv

```sh
$ python3 vimeo-download.py example.tsv
```

## TSV Format
The app uses a TSV (TAB-separate values) file to download your desired list of videos at target quality rates. Four items can be provided with two of them being required:
- video quality (optional)
  - V240
  - V360
  - V540
  - V720
  - V1080
  - V1440
  - V2160
  - VMAX (download highest resolution available)
- audio quality (optional)
  - LOW
  - MED
  - HI
- mp4 output file (required)
- master.json url (required)

format:
```
# standard
# <video-quality><TAB><audio-quality><TAB><output-file><TAB><master-json-url>

# minimum
# <TAB><TAB><output-file><TAB><master-json-url>
```
example.tsv
```
V720	HI	test_1.mp4	https://144vod-adaptive.akamaized.net/<long-url>/master.json?base64_init=1&query_string_ranges=1
VMAX	MED	test_2.mp4	https://108vod-adaptive.akamaized.net/<long-url>/master.json?base64_init=1
VMAX	HI	test_3.mp4	https://42vod-adaptive.akamaized.net/<long-url>/master.json?base64_init=1&query_string_ranges=1
		test_4.mp4	https://80vod-adaptive.akamaized.net/<long-url>/master.json?base64_init=1&query_string_ranges=1
		test_5.mp4	https://58vod-adaptive.akamaized.net/<long-url>/master.json?base64_init=1&query_string_ranges=1
```

## Find master.json
1. in your browser, go to video you want to download
2. open develepor tools (chrome: F12)
3. select network tab
4. refresh page, pause video if it autoplays
5. Look for master.json ![network_master_json](doc/network_master_json.png)
6. right click > copy > copy url

## Acknowledgements
This wouldn't be possible without the work of another repo which did all of the heavy lifting.  
I simply made some fixes and added a few features.

- @AbCthings: https://github.com/AbCthings/vimeo-audio-video