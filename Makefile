PREFIX=docker.heinrichhartmann.net
IMAGE=${PREFIX}/pile-video
PWD=$$(pwd)

# export make variables to subshells
export

DEBUG=1
NO_SWEEP=1
VIDEOS=/share/hhartmann/garage/Videos/
PILE=/share/hhartmann/garage/Videos/pile/
CACHE=/share/hhartmann/garage/Vcache
TMP=/share/hhartmann/garage/Vtmp
MP3=./var-test/mp3
PORT=8083

serve:
	poetry run python main.py

docker-image:
	poetry export -o requirements.txt
	docker build . -t ${IMAGE}

docker-serve:
	mkdir -p videos/pile cache tmp mp3
	docker run -p 8090:8083 -v ${PWD}/downloads:/usr/src/app/downloads -v ${PWD}/cache:/usr/src/app/cache -v ${PWD}/videos:/usr/src/app/videos -v ${PWD}/videos:/usr/src/app/mp3 -it ${IMAGE}

docker-push:
	docker push ${IMAGE}

tailwind:
	npx tailwindcss-cli build -c tailwind.config.js -o static/css/tailwind.css
