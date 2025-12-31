# Single File Bookmark Archiver

Automatically archives Firefox bookmarks to HTML files using SingleFile CLI.

## Features

- Finds a specified Firefox bookmark folder for your default profile, and archives newly found bookmarks within it
- Keeps track of previously archived urls in a super simple text file
- Automatically scheduled on Linux via systemd. Install script sets up a systemd user service and timer.
- Publishes to an MQTT Server to tie in to monitoring

## Relies on
- [single-file-cli](https://github.com/gildas-lormeau/single-file-cli)
    - Saves complete pages (HTML + images embedded)
    - Includes timestamp in filenames
- Firefox sync

## Useful for
I created this to get around the fact that there is no single-file extension on iOS for Firefox. With this and relying on Firefox sync, I bookmark a link to a specific folder on any device, let it sync to all my devices, and rely on the systemd script to run on my main machine, which archives the newly found links. My archive location is backed up for resiliency.

## Notes

- Bookmarks are read from your local filesystem under ~/.mozilla/firefox/<your profile>
  * your default profile is inferred from your `~/.mozilla/firefox/profiles.ini` file
  * these bookmarks only seem to be synced once a day from firefox. I'm not sure how to make this more instantaneous.
- Bookmarks remain in Firefox archive bookmark folder after the single-file archive. 
  * I was reticent to edit bookmarks on the local filesystem but maybe there is a way
- Script only processes URLs not in the "already-processed" log file
- Archived files named: `YYYY-MM-DD_HH-MM-SS_Page-Title.html`
- Firefox must be installed and have run at least once

## Setup

### 0. Create Bookmark Folder in Firefox

1. Open Firefox
2. Bookmarks → Manage Bookmarks (Ctrl+Shift+O)
3. Create a new folder named "to_archive" (or whatever you configured)
4. Add some bookmarks to the new folder

### 1. Install

```bash
# Install SingleFile CLI (assumes npm is already installed)
npm install "single-file-cli"

# setups systemd service
bash setup.sh

# Manually update config.yaml (as listed in step2)

# Wait a day...
# Start service and monitor output (note that firefox syncs bookmarks to your filesystem about once a day)
systemctl --user start single-file-bookmark-archiver
journalctl --user -u single-file-bookmark-archiver.service"


```

### 2. Manually configure Yaml under ~/.config/single_file_bookmark_archiver/config.yaml

Parameters:
- `bookmark_folder_name`: Name of the Firefox bookmark folder to monitor
- `archive_destination`: Where to save archived HTML files
- `processed_urls_log`: Path to log file tracking processed URLs
- `firefox_profile`: Path to Firefox profile (null = auto-detect)

## Usage

### Manual Run

```bash
# Install Python dependencies
uv sync
source .venv/bin/activate && python bookmark_archiver.py
# OR
uv run bookmark_archiver.py
```

Or with custom config if you want:

```bash
python bookmark_archiver.py /path/to/random-config.json
```

### Automatic (Systemd)

* Runs daily
* setup.sh setups a user service and timer

## Workflow

1. **On any device:** Add bookmark to "to_archive" folder in Firefox (or whatever you've named it)
2. **Firefox Sync:** Syncs bookmark to all devices
3. **On Linux desktop:** Script runs via systemd
4. **Script:**
   - Reads latest Firefox bookmark backup
   - Finds new URLs in "to_archive" folder
   - Downloads each page with SingleFile
   - Saves to archive directory with timestamp
   - Logs URL as processed

## Syncing with Syncthing

Point Syncthing at your `archive_destination` directory to sync archives across devices.


## Troubleshooting

**"lz4 package required":**
```bash
uv add lz4
```

**"single-file: command not found":**
```bash
npm install "single-file-cli"
```

**"No Firefox profile found":**
- Ensure Firefox is installed
- Run Firefox at least once
- Or specify profile path in config

**Firefox profile auto-detection fails:**
Set `firefox_profile` in config to your profile path:
```
~/.mozilla/firefox/xxxxxxxx.default-release
```
