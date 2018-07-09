
echo "[+] Install requirements ..."
sudo apt update
sudo apt-get install python-dev build-essential libssl-dev libffi-dev \
    libxml2-dev libxslt1-dev zlib1g-dev \
    python-pip python3-pip iputils-ping tmux wget unzip -y

sudo pip install -r requirements.txt
sudo pip3 install -r ovc_master_hosted/Portal/requirements.txt
sudo chmod 777 ovc_master_hosted/Portal

echo "[+] Download chrome driver for portal tests ..."
sudo apt-get install -y xvfb chromium-chromedriver -y
sudo ln -fs /usr/lib/chromium-browser/chromedriver /usr/bin/chromedriver
sudo ln -fs /usr/lib/chromium-browser/chromedriver /usr/local/bin/chromedriver


#export PYTHONPATH=/opt/jumpscale7/lib:/opt/jumpscale7/lib/lib-dynload/:/opt/jumpscale7/bin:/opt/jumpscale7/lib/python.zip:/opt/jumpscale7/lib/plat-x86_64-linux-gnu


