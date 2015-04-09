# Voting helper

Perhaps a description will follow here some time.

## Usage

Make a copy of `conf.example.ini` called `conf.ini` and change the values as you require.

Invoke `./vote.py` as follows:  
`vote.py [-h] [--logfile LOGFILE] action [target]`  

`action` can either be
- **vote**: to vote only once and terminate, or
- **watch**: to vote every interval set in the `conf.ini`

`target` is optional and names the section in `conf.ini` from which to draw the settings.
