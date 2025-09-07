# Rate My Courses

## Deployment

- Install Docker
- Create a .env file and copy it to the server
- Create a dockerfile for the django service
- Create a docker compose file defining all the services
- Create a systemd service to make sure the stack starts on restart
- Create a github action that builds the container and uploads it to ghcr.io so watchtower can redeploy the new version

```bash
# /etc/systemd/system/ratemycourses.service
[Unit]
Description=Ratemycourses docker compose stack
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
WorkingDirectory=/srv/ratemycourses
RemainAfterExit=yes
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ratemycourses
```

## First Setup

- use `docker compose exec createsuperuser` to create a new admin account

