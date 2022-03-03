FROM python:3@sha256:dcd7ce888fb44f050d76e8faf5a910c07ed9f146c78320c29e9466fdf2b6df07


# Install ffmpeg.
# https://unix.stackexchange.com/questions/508724/failed-to-fetch-jessie-backports-repository
RUN echo "deb [check-valid-until=no] http://cdn-fastly.deb.debian.org/debian jessie main" > /etc/apt/sources.list.d/jessie.list
RUN echo "deb [check-valid-until=no] http://archive.debian.org/debian jessie-backports main" > /etc/apt/sources.list.d/jessie-backports.list
RUN sed -i '/deb http:\/\/deb.debian.org\/debian jessie-updates main/d' /etc/apt/sources.list
# https://askubuntu.com/questions/13065/how-do-i-fix-the-gpg-error-no-pubkey
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 7638D0442B90D010 CBF8D6FD518E17E1 8B48AD6246925553
RUN apt-get -o Acquire::Check-Valid-Until=false --allow-unauthenticated update
RUN apt-get install -y libav-tools xz-utils
RUN pip install -U youtube-dl
# apt's ffmpeg conflicts with libav; Install static versions from https://johnvansickle.com/ffmpeg/ instead
RUN mkdir -p /opt/ffmpeg && \
  curl https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-amd64-static.tar.xz | xzcat | tar -xvf - -C /opt/ffmpeg
RUN cd /opt/ffmpeg/ffmpeg-* && ln -s "${PWD}/ffmpeg" /usr/local/bin/

RUN mkdir -p /usr/src/app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /usr/src/app
WORKDIR /usr/src/app
CMD [ "/bin/bash", "/usr/src/app/cmd.sh" ]
EXPOSE 8080
