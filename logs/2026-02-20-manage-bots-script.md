# Log: Bot management script on macbook-i7

## 2026-02-20

### Step 1: Write manage-bots.sh via SSH

Writing the script to macbook-i7 via SSH cat heredoc...

Script written successfully: `/Users/andrewmaier/manage-bots.sh` (6188 bytes, -rwxr-xr-x).

### Step 2: Test with `status` command

Running `./manage-bots.sh status` via SSH...

Output:
```
Bot status:

  ●  youtubeDownloaderBot  — stopped
  ●  VocabTrAiBot  — stopped
  ●  translatorBot  — dead (stale PID 78631)
  ●  datesKeeperBot  — stopped
  ●  fortune-teller  — stopped
```

All 5 bots detected. translatorBot has a stale PID file (process 78631 no longer alive).
The others have no PID files (either never started via this script, or genuinely stopped).

Done. Script is working.
