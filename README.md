# edatmo-obs-sftp
 Python script to manage the safe and reliable transfer of raw observation data to remote sftp server. Sample usage:


 ```
python edatmo-obs-sftp.py --config_file my_config_file.json
```

## Setup

### 1. Clone the repo

```
git clone https://github.com/edatmo/edatmo-obs-sftp
```

### 2. Copy the config file

```
cp _config.json my_config.json
```


### 3. Edit the config file


```javascript
{
  "params": {
// the sftp hostname
    "host": "sshpa.geos.ed.ac.uk",
// the sftp username
    "user": "edatmo01",
// the sftp port number
    "port": 6022,
// the place on your computer where you want the files to go after being successfully uploaded
    "local_archive_dir": "/cygdrive/c/users/willm/Desktop/test_archive/",
// remove empty local directories if they are older than n seconds
    "remove_empty_local_dirs_older_than_s": 172800
  },
// a list of configurations for each file type
  "file_settings": [
    {
// the base directory where the files are fouind on the local computer
      "local_base_dir": "/cygdrive/c/Users/willm/Desktop/EM27_test_environment/Public/Documents/EM27/CAMTRACKER/Bilder",
// files with the following file pattern will be uploaded
      "file_pattern": "????.??.??_??.??.??_Exp*.JPG",
// files will be uploaded to this remote directory
      "remote_base_dir": "data/EM27/215/Bilder",
// only upload files older than `upload_older_than_s` seconds
      "upload_older_than_s": 0,
// after a file is older than local_archive_older_than_s, no longer upload the file. Instead, move file to local_archive_dir
      "local_archive_older_than_s": 0,
// remove empty subdirectories within local_base_dir? (only if older than remove_empty_local_dirs_older_than_s)
      "remove_empty_subdirs": true,
// allow the files to be moved to the local archive. If false, then the files will always be re-uploaded . 
      "allow_local_archive": true
    }
}
```

### Issues/notes

- If on windows: suggest use mobaxterm or similar tool for executing unix commands (e.g. cygwin)
- If the `remote_base_dir` doesn't exist, the program will fail. Create the `remote_base_dir` manually in advance. 

