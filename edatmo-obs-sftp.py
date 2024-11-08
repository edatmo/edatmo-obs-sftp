# -*- coding: utf-8 -*-
"""
Created on Wed Oct 30 11:19:04 2024

@author: willm
"""

import os
from glob import glob
import shutil
import json
import argparse
from dataclasses import dataclass
import logging
import time


@dataclass
class Params:
    host: str
    user: str
    port: int
    archive_dir: str
    remove_empty_local_dirs_older_than_s: int

    def __post_init__(self):
        if not self.host:
            raise ValueError("host cannot be empty")

        if not self.user:
            raise ValueError("user cannot be empty")

        if not isinstance(self.port, int) or self.port <= 0:
            raise ValueError("port must be a positive integer")

        if not self.archive_dir:
            raise ValueError("archive_dir cannot be empty")

        if not isinstance(self.remove_empty_local_dirs_older_than_s, int) or \
                self.remove_empty_local_dirs_older_than_s <= 0:
            raise ValueError(
                "remove_empty_local_dirs_older_than_s must be a positive integer")

    def build_mkdir_command(self, remote_dir):
        return f'sftp -P {self.port} -q {self.user}@{self.host} <<< $"mkdir {remote_dir}"'

    def build_scp_command(self, local_file, remote_dir):
        return f'scp -P {self.port} -s -r -p -q {local_file} {self.user}@{self.host}:/{remote_dir}/'


@dataclass
class FileSettings:
    local_base_dir: str
    file_pattern: str
    remote_base_dir: str
    upload_older_than_s: int
    archive_older_than_s: int
    has_subdir: bool
    allow_local_archive: bool

    def __post_init__(self):
        if not os.path.isdir(self.local_base_dir):
            raise ValueError(f"local_base_dir '{self.local_base_dir}' does not exist")

        if not self.file_pattern:
            raise ValueError("file_pattern cannot be empty")

        if not self.filepattern_is_sensible():
            raise ValueError(
                f"file_pattern {self.file_pattern} is too ambiguous. Example patterns: "
                f"WXT536_????????_??????.dat or WXT*_????????_??????.*. This is to "
                f"prevent moving around unexpected files."
            )

        if not self.remote_base_dir:
            raise ValueError("remote_base_dir cannot be empty")

        if self.upload_older_than_s is not None and self.upload_older_than_s < 0:
            raise ValueError("upload_older_than_s must be non-negative")

        if self.archive_older_than_s is not None and self.archive_older_than_s < 0:
            raise ValueError("archive_older_than_s must be non-negative")

        if not isinstance(self.has_subdir, bool):
            raise ValueError("has_subdir must be a boolean")

        if not isinstance(self.allow_local_archive, bool):
            raise ValueError("allow_local_archive must be a boolean")

    def filepattern_is_sensible(self):
        if (len(self.file_pattern.replace("*", "")) < 5) or (len(self.file_pattern) < 5):
            return False
        return True

    def remove_old_empty_directories_recursive(self, params):

        try:
            for entry in os.scandir(self.local_base_dir):
                if entry.is_dir():
                    sub_dir = os.path.join(self.local_base_dir, entry.name)
                    if os.listdir(sub_dir):
                        continue
                    if _time_since_last_modification_s(sub_dir) > \
                            params.remove_empty_local_dirs_older_than_s:
                        logging.debug(f"Removing old empty directory {sub_dir}")
                        os.rmdir(sub_dir)
        except OSError as e:
            logging.error(f"Error removing directory {file_settings.dir_path}: {e}")

    def file_old_enough_for_upload(self, file_path):
        modification_time = _time_since_last_modification_s(file_path)

        if modification_time < self.upload_older_than_s:
            return False
        else:
            return True

    def file_old_enough_for_archive(self, file_path):
        modification_time = _time_since_last_modification_s(file_path)

        if modification_time < self.archive_older_than_s:
            return False
        else:
            return True


def parse_config(config_file) -> (Params, [FileSettings]):
    with open(config_file, 'r') as f:
        config_json = json.load(f)

    params = Params(**config_json["params"])

    file_settings_list = [FileSettings(**file_settings)
                          for file_settings in config_json["file_settings"]]

    return params, file_settings_list


def _time_since_last_modification_s(file_path):
    file_stat = os.stat(file_path)
    last_modified_time = file_stat.st_mtime
    current_time = time.time()
    return current_time - last_modified_time


def sftp_upload(params: Params, file_settings: FileSettings):

    if file_settings.has_subdir:
        file_settings.remove_old_empty_directories_recursive(params)
        subdirs = [os.path.basename(d) for d in glob(
            file_settings.local_base_dir + "/*") if os.path.isdir(d)]
    else:
        subdirs = [""]

    for subdir in subdirs:
        subdir_fullpath = os.path.join(file_settings.local_base_dir, subdir)
        subdir_pattern = os.path.join(subdir_fullpath, file_settings.file_pattern)
        files = glob(subdir_pattern)

        if not files:
            logging.info(f"No files found in {subdir_pattern}")
            continue

        if files and file_settings.has_subdir:
            cmd_mkdir = params.build_mkdir_command(
                f"{file_settings.remote_base_dir}/{subdir}")
            logging.info(cmd_mkdir)
            result = os.system(cmd_mkdir)
            logging.debug(f"Command {cmd_mkdir} gave exit status: {result}")

        for file in files:
            logging.debug(f"Evaluating file {file} ...")
            if not file_setting.file_old_enough_for_upload(file):
                continue

            if os.path.isdir(file):
                logging.warning(
                    f"{file} is a directory. Cannot handle nested directories.")
                continue

            file = os.path.normpath(file)
            cmd_scp = params.build_scp_command(
                file, f"{file_settings.remote_base_dir}/{subdir}")
            logging.info(cmd_scp)
            result = os.system(cmd_scp)
            logging.debug(f"Command {cmd_scp} gave exit status: {result}")

            if result == 0 and file_setting.file_old_enough_for_archive(file) and \
                    file_settings.allow_local_archive:
                logging.debug(
                    f"Successfully uploaded {file} and the file is old enough to archive")
                archive_subdir = os.path.basename(file_settings.remote_base_dir)
                destination_path = os.path.normpath(os.path.join(
                    params.archive_dir, archive_subdir, subdir))
                os.makedirs(destination_path, exist_ok=True)
                destination_path_full = os.path.join(
                    destination_path, os.path.basename(file))
                logging.debug(f"Moving {file} to archive {destination_path_full}")
                try:
                    shutil.move(file, destination_path_full)
                except OSError as e:
                    logging.error(
                        f"Moving {file} to {destination_path_full} gave error {e}")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--config_file", type=str, default="config.json",
                        help="Path to the configuration file")
    parser.add_argument('--loglevel',
                        default='info',
                        help='Provide logging level. Example --loglevel debug, default=info')

    args = parser.parse_args()
    logging.basicConfig(level=args.loglevel.upper(),
                        format='%(asctime)s - %(levelname)s - %(message)s')

    params, file_settings = parse_config(args.config_file)

    for file_setting in file_settings:
        sftp_upload(params, file_setting)
