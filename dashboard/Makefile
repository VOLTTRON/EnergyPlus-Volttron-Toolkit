all: pull dashboard nginx
	@echo "Update Done."

pull:
	sudo git pull

dashboard:
	sudo systemd restart dashboard.service

nginx:
	service nginx restart

