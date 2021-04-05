FROM python:3

# Install ffmpeg.
# https://unix.stackexchange.com/questions/508724/failed-to-fetch-jessie-backports-repository
RUN echo "deb [check-valid-until=no] http://cdn-fastly.deb.debian.org/debian jessie main" > /etc/apt/sources.list.d/jessie.list
RUN echo "deb [check-valid-until=no] http://archive.debian.org/debian jessie-backports main" > /etc/apt/sources.list.d/jessie-backports.list
RUN sed -i '/deb http:\/\/deb.debian.org\/debian jessie-updates main/d' /etc/apt/sources.list
RUN apt-get -o Acquire::Check-Valid-Until=false update
RUN apt-get install -y libav-tools xz-utils
RUN pip install -U youtube-dl
# apt's ffmpeg conflicts with libav; Install static versions from https://johnvansickle.com/ffmpeg/ instead
RUN mkdir -p /opt/ffmpeg && \
  curl https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-amd64-static.tar.xz | xzcat | tar -xvf - -C /opt/ffmpeg
RUN cd /opt/ffmpeg/ffmpeg-* && ln -s "${PWD}/ffmpeg" /usr/local/bin/

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
COPY requirements.txt /usr/src/app/
RUN pip install -r requirements.txt

COPY /run.sh /
CMD [ "/bin/bash", "/run.sh" ]

COPY . /usr/src/app
RUN ln -s /usr/src/app/mnt/downloads /downloads
RUN ln -s /usr/src/app/mnt/videos /videos
VOLUME ["/downloads", "/videos"]

EXPOSE 8080
