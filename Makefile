PREFIX=docker.heinrichhartmann.net:5000
IMAGE=${PREFIX}/pile-video
PWD=$$(pwd)

run:
	poetry run python main.py

docker-image:
	poetry export -o requirements.txt
	docker build . -t ${IMAGE}

docker-push:
	docker push ${IMAGE}

docker-run:
	docker run -p 8090:8080 -v ${PWD}/downloads:/usr/src/app/downloads -v ${PWD}/cache:/usr/src/app/cache -v ${PWD}/videos:/usr/src/app/videos -it docker.heinrichhartmann.net:5000/youtube-dl

tailwind:
	npx tailwindcss-cli build -c tailwind.config.js -o static/css/tailwind.css

