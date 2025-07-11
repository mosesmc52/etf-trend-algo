CONTAINER_ID := $(shell docker ps --filter name=etf-trend-algo_etf-trend-algo --format '{{.ID}}')

shell:
	docker exec -it $(CONTAINER_ID) bash

build:
	docker-compose -f docker-compose.yml build

up:
	docker-compose -f docker-compose.yml up

daemon:
	docker-compose -f docker-compose.yml up -d
