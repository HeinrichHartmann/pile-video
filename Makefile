PREFIX=docker.heinrichhartmann.net:5000
IMAGE=${PREFIX}/youtube-dl


docker-image:
	docker build . -t ${IMAGE}

docker-push:
	docker push ${IMAGE}

clean-media:
	rm -rf ./downloads; mkdir -p downloads

run:
	poetry run python youtube-dl-server.py
