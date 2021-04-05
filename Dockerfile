FROM python:3

# Install ffmpeg.
#https://unix.stackexchange.com/questions/508724/failed-to-fetch-jessie-backports-repository
RUN echo "deb [check-valid-until=no] http://cdn-fastly.deb.debian.org/debian jessie main" > /etc/apt/sources.list.d/jessie.list
RUN echo "deb [check-valid-until=no] http://archive.debian.org/debian jessie-backports main" > /etc/apt/sources.list.d/jessie-backports.list
RUN sed -i '/deb http:\/\/deb.debian.org\/debian jessie-updates main/d' /etc/apt/sources.list
RUN apt-get -o Acquire::Check-Valid-Until=false update
RUN apt-get install -y libav-tools vim dos2unix && \
    rm -rf /var/lib/apt/lists/*

RUN pip install -U youtube-dl

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
COPY requirements.txt /usr/src/app/
RUN pip install -r requirements.txt

COPY /run.sh /
RUN  ln -s /usr/src/app/downfolder / && \
     chmod +x /run.sh && \
     dos2unix /run.sh

COPY . /usr/src/app

EXPOSE 8080

VOLUME ["/downfolder"]

CMD [ "/bin/bash", "/run.sh" ]
