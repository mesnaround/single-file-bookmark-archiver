#!/usr/bin/env bash


CONFIG_DIR=$HOME/.config/single_file_bookmark_archiver
LOCAL_INSTALL_DIR=$HOME/.local/share/single_file_bookmark_archiver

set -xve

[ -d $CONFIG_DIR ] && rm $CONFIG_DIR/* && rmdir $CONFIG_DIR
[ -d $LOCAL_INSTALL_DIR ] && rm $LOCAL_INSTALL_DIR/* && rm -rf $LOCAL_INSTALL_DIR/.venv && rmdir $LOCAL_INSTALL_DIR

rm $HOME/.config/systemd/user/single-file-bookmark-archiver.*

systemctl --user disable single-file-bookmark-archiver.timer
systemctl --user stop single-file-bookmark-archiver.timer
systemctl --user daemon-reload
