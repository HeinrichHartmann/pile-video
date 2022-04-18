FROM ubuntu:20.04

RUN apt-get update -qq
RUN apt-get install -y ffmpeg
RUN apt-get install -y python3 python3-pip
RUN apt-get install -y tzdata && ln -fs /usr/share/zoneinfo/Etc/UTC /etc/localtime && dpkg-reconfigure -f noninteractive tzdata

RUN mkdir -p /usr/src/app
COPY requirements.txt .
RUN pip3 install -r requirements.txt

COPY . /usr/src/app
WORKDIR /usr/src/app
CMD [ "/bin/bash", "/usr/src/app/cmd.sh" ]
EXPOSE 8080
