# ibc
Identity Block Chain <br>
---
## Prerequisits

Ubuntu 22.04

## Installation

More detailed installation instructions including firewall configuration if needed are [here](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-20-04).

1. Install Nginx
```
sudo apt update
sudo apt install nginx
```
2. Install MongoDB
```
sudo apt-get install gnupg curl
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt-get update
sudo apt-get install -y mongodb-org
sudo systemctl daemon-reload
sudo systemctl start mongod
sudo systemctl enable mongod
sudo systemctl status mongod
```
3. Install redis stack server
```
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
sudo chmod 644 /usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
sudo apt-get update
sudo apt-get install redis-stack-server
sudo systemctl start redis-stack-server.service
sudo systemctl enable redis-stack-server.service
sudo systemctl status redis-stack-server.service
```
4. Install python
```
sudo apt install python3-pip python3-dev build-essential libssl-dev libffi-dev python3-setuptools
sudo apt install python3-venv
```
5. Install ibc
```
git clone https://github.com/ouripoupko/ibc.git
cd ibc
```
6. Create a virtual environment
```
python3 -m venv vibcenv
source vibcenv/bin/activate
```
7. Install dependencies
```
pip install wheel
pip install -r requirements.txt
deactivate
```
8. Create the following service files
```bash
# /etc/systemd/system/ibc.service:
[Unit]
Description=Gunicorn instance to serve ibc
After=network.target
Wants=ibc.execution.service
Wants=ibc.consensus.service

[Service]
User=ouri_poupko
Group=www-data
WorkingDirectory=/home/ouri_poupko/ibc
Environment="PATH=/home/ouri_poupko/ibc/vibcenv/bin"
ExecStart=/home/ouri_poupko/ibc/vibcenv/bin/gunicorn --workers 3 --bind unix:ibc.sock --worker-class gevent --error-logfile error.log --access-logfile access.log -m 007 wsgi:app

[Install]
WantedBy=multi-user.target
```
	/etc/systemd/system/ibc.consensus.service

[Unit]
PartOf=ibc.service

[Service]
User=ouri_poupko
Group=www-data
WorkingDirectory=/home/ouri_poupko/ibc
Environment="PATH=/home/ouri_poupko/ibc/vibcenv/bin"
ExecStart=/home/ouri_poupko/ibc/vibcenv/bin/python3 consensus_service.py

[Install]
WantedBy=multi-user.target

	/etc/systemd/system/ibc.execution.service
 
[Unit]
PartOf=ibc.service

[Service]
User=ouri_poupko
Group=www-data
WorkingDirectory=/home/ouri_poupko/ibc
Environment="PATH=/home/ouri_poupko/ibc/vibcenv/bin"
ExecStart=/home/ouri_poupko/ibc/vibcenv/bin/python3 execution_service.py

[Install]
WantedBy=multi-user.target

7. Run the services

	sudo systemctl start ibc

	sudo systemctl enable ibc

	sudo systemctl status ibc

8. Create the Nginx site

	/etc/nginx/sites-available/ibc:

server {
    listen 80;
    listen [::]:80;

    server_name gdi.gloki.contact;

    location / {
        return 301 /pda;
    }

    location /ibc {
        include proxy_params;
        proxy_pass http://unix:/home/ouri_poupko/ibc/ibc.sock;
        proxy_set_header Access-Control-Allow-Origin *;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    location /stream {
        include proxy_params;
        proxy_pass http://unix:/home/ouri_poupko/ibc/ibc.sock;
        proxy_buffering off;
    }
    location /pda/ {
        root /srv/site;
        proxy_cache off;
        try_files $uri /pda/index.html$is_args$args;
    }
    location /pda {
        return 301 /pda/$is_args$args;
    }
    location /delib/ {
        root /srv/site;
        proxy_cache off;
        try_files $uri /delib/index.html$is_args$args;
    }
    location /delib {
        return 301 /delib/$is_args$args;
    }
    location /community/ {
        root /srv/site;
        proxy_cache off;
        try_files $uri /community/index.html$is_args$args;
    }
    location /community {
        return 301 /community/$is_args$args;
    }
    location /profile/ {
        root /srv/site;
        proxy_cache off;
        try_files $uri /profile/index.html;
    }
    location /profile {
        return 301 /profile/$is_args$args;
    }
    location /social/ {
        root /srv/site;
        proxy_cache off;
        try_files $uri /social/index.html;
    }
    location /social {
        return 301 /social/$is_args$args;
    }
    location /gloki/ {
        root /srv/site;
        proxy_cache off;
        try_files $uri /gloki/index.html;
    }
    location /gloki {
        return 301 /gloki/$is_args$args;
    }
}

9. Activate it

	sudo ln -s /etc/nginx/sites-available/ibc /etc/nginx/sites-enabled

	sudo rm /etc/nginx/sites-enabled/default

11. Get a certificate

	sudo apt install python3-certbot-nginx

	sudo certbot --nginx -d gdi.gloki.contact

12. Create the following files

	/etc/nginx/snippets/self-signed.conf:

ssl_certificate /etc/ssl/certs/nginx-selfsigned.crt;
ssl_certificate_key /etc/ssl/private/nginx-selfsigned.key;

	/etc/nginx/snippets/ssl-params.conf:

ssl_protocols TLSv1.3;
ssl_prefer_server_ciphers on;
ssl_dhparam /etc/nginx/dhparam.pem; 
ssl_ciphers EECDH+AESGCM:EDH+AESGCM;
ssl_ecdh_curve secp384r1;
ssl_session_timeout  10m;
ssl_session_cache shared:SSL:10m;
ssl_session_tickets off;
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;
# Disable strict transport security for now. You can uncomment the following
# line if you understand the implications.
#add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header X-XSS-Protection "1; mode=block";


13. Modify the site conf (It seems certbot does it by itself)

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    include snippets/self-signed.conf;
    include snippets/ssl-params.conf;

    server_name gdi.gloki.contact;

    location / {
        return 301 /pda;
    }

    location /ibc {
        include proxy_params;
        proxy_pass http://unix:/home/ouri_poupko/ibc/ibc.sock;
        proxy_set_header Access-Control-Allow-Origin *;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    location /stream {
        include proxy_params;
        proxy_pass http://unix:/home/ouri_poupko/ibc/ibc.sock;
        proxy_buffering off;
    }
    location /pda/ {
        root /srv/site;
        proxy_cache off;
        try_files $uri /pda/index.html$is_args$args;
    }
    location /pda {
        return 301 /pda/$is_args$args;
    }
    location /delib/ {
        root /srv/site;
        proxy_cache off;
        try_files $uri /delib/index.html$is_args$args;
    }
    location /delib {
        return 301 /delib/$is_args$args;
    }
    location /community/ {
        root /srv/site;
        proxy_cache off;
        try_files $uri /community/index.html$is_args$args;
    }
    location /community {
        return 301 /community/$is_args$args;
    }
    location /profile/ {
        root /srv/site;
        proxy_cache off;
        try_files $uri /profile/index.html;
    }
    location /profile {
        return 301 /profile/$is_args$args;
    }
    location /social/ {
        root /srv/site;
        proxy_cache off;
        try_files $uri /social/index.html;
    }
    location /social {
        return 301 /social/$is_args$args;
    }
    location /gloki/ {
        root /srv/site;
        proxy_cache off;
        try_files $uri /gloki/index.html;
    }
    location /gloki {
        return 301 /gloki/$is_args$args;
    }
}
server {
    listen 80;
    listen [::]:80;

    server_name gdi.gloki.contact;

    return 301 https://$server_name$request_uri;
}

14. Add Nginx user (www-data) to your group

	sudo usermod -a -G ouri_poupko www-data

	id www-data

16. Restart Nginx

	sudo nginx -t

	sudo systemctl restart nginx

