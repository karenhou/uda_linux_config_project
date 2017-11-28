# uda_linux_config_project
This is the final project for udacity full-stack web developer course. In this project Amazon's Lightsail VM(ubuntu) is used to host previous built website: Catalog

<img src="https://user-images.githubusercontent.com/6285935/33249083-67d3cffc-d363-11e7-9ca8-5bd4fa23a755.png" width="90%"></img>



## Deployment
Here are the steps I took to complete this project.

#### 1. Setup VM on Amazon Lightsail
[Tutorial: Amazon Lightsail: How to set up your first instance](https://cloudacademy.com/blog/how-to-set-up-your-first-amazon-lightsail/)

#### 2. Login ubuntu via SSH
<img src="https://user-images.githubusercontent.com/6285935/33249867-dc834b6c-d367-11e7-94d6-4af3523b4153.png" width="50%"></img>

- Click on the account page can lead you to

<img src="https://user-images.githubusercontent.com/6285935/33249901-1b396ed6-d368-11e7-8fe1-3b35493b375b.png" width="50%"></img>

- Download the the private key

- Change permission
```
chmod 600 LightsailDefaultPrivateKey-xxxx.pem
```

- To access the server
```
ssh -i LightsailDefaultPrivateKey-xxxx.pem ubuntu@YOURAWSPUBLICIP
```

#### 3. Update server apps
```
sudo apt-get update
sudo apt-get upgrade
```

- Install finger for user management in ubuntu
```
sudo apt-get install finger
```

- Install python-minimal if you use python 2 to build your project
```
sudo apt-get install python-minimal
```

#### 4. Create a new user: grader
```
sudo adduser grader
sudo nano /etc/sudoers.d/grader
```

- Add `grader ALL=(ALL:ALL) ALL` to `/etc/sudoers.d/grader`

- Switch back to local cmd window to generate SSH keypairs
```
ssh-keygen
```

- You can specify where and what name it the key should be stored. I call it `grader` It then will generates 2 files: **grader** and **grader.pub**

- Rename private key and change permissions
```
mv grader grader.rsa
chmod 600 grader.pub
```

- Copy content of `grader.pub`

- Switch back to your VM
```
sudo mkdir /home/grader/.ssh
sudo nano /home/grader/.ssh/authorized_keys
```

- Paste copied public key content into authorized_keys
```
sudo chmod 700 /home/grader/.ssh
sudo chown grader:grader /home/grader/.ssh
sudo chmod 600 /home/grader/.ssh/authorized_keys
sudo chown grader:grader /home/grader/.ssh/authorized_keys
sudo service ssh restart
```

- Open a new prompt window and login as grader
```
ssh -i grader.rsa grader@YOURAWSPUBLICIP
```

- If you run into some error you can try add `-vvv` in the cmd to debug
```
ssh -i -vvv grader.rsa grader@YOURAWSPUBLICIP
```

#### 5. Add SSH ports
```
sudo nano /etc/ssh/sshd_config
```

- Add `port 2200` (I add `port 2200` without removing `port 22` just in case I failed this setup and accidentally lock access port. You can remove `port 22` after you made sure you can access via `port 2200`)

- Remove root login by changing `PermitRootLogin` to `no`

- Remove password login by changing `PasswordAuthentication` to `no`

- Save the file and restart ssh
```
sudo service ssh restart
```

- Log out then try to access via `port 2200`
```
ssh -i grader.rsa grader@YOURAWSPUBLICIP -p 2200
```

#### 6. Setup firewall via ufw
```
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 2200
sudo ufw allow 2200/tcp
sudo ufw allow 80
sudo ufw allow 80/tcp
sudo ufw allow 123
sudo ufw allow 123/tcp
sudo ufw enable
sudo ufw status
```

#### 7. Setup UTC timezone

- Check time zone by cmd `date`

- Modify timezone by cmd
```
sudo nano /etc/timezone
```

- Enter `Etc/UTC` and save

#### 8. Install Apache HTTP Server / WSGI / GIT / Setup Repo
```
sudo apt-get install apache2
sudo apt-get install python-setuptools
sudo apt-get libapache2-mod-wsgi
```

- Enable wsgi
```
sudo a2enmod wsgi
```

- Restart Apache
```
sudo service apache2 restart
```

- Setup GIT
```
sudo apt-get install git
```

- Setup user name and email for Git
```
git config --global user.name 'YOUR USER NAME'
git config --global user.email 'YOUR EMAIL'
```

- Setup git repository
```
cd /var/www
sudo mkdir catalog
cd catalog
sudo git clone https://github.com/karenhou/uda_linux_config_project.git catalog
```

- Your cloned repo should now be under `/var/www/catalog/catalog`

#### 9. Install Tools and Setup environments
```
cd /var/www/catalog/
```

- You should now see your repo folder(last catalog project you create). We'll then add the rest for it to work

- My finished directory looks like this
<img src="https://user-images.githubusercontent.com/6285935/33256293-680418a0-d38c-11e7-93d9-f24ef7c78d8e.png" width="100%"></img>

- Install PIP
```
sudo apt-get install python-pip
```

- Setup virtual environment
```
sudo pip install virtualenv
sudo virtualenv venv
sudo source venv/bin/activate
```

- Install dependency for this project
```
sudo pip install Flask
sudo pip install sqlalchemy
sudo pip install Flash-SQLAlchemy
sudo pip install psycopg2
sudo apt-get install python-psycopg2
sudo pip install oauth2client
sudo pip install httplib2
sudo pip install requests
```

#### 10. Setup Virtual Host in Apache
```
sudo nano /etc/apache2/sites-available/catalog.conf
```

- Add following into `catalog.conf`
```
<VirtualHost *:80>
ServerName 13.230.63.149
ServerAdmin admin@mywebsite.com
WSGIScriptAlias / /var/www/catalog/catalog.wsgi
<Directory /var/www/catalog/catalog/>
        Order allow,deny
        Allow from all
</Directory>
Alias /static /var/www/catalog/catalog/static
<Directory /var/www/catalog/catalog/static/>
        Order allow,deny
        Allow from all
</Directory>
ErrorLog ${APACHE_LOG_DIR}/error.log
LogLevel warn
CustomLog ${APACHE_LOG_DIR}/access.log combined
</VirtualHost>
```

- Enable Host
```
sudo a2ensite catalog
```

#### 11. Setup WSGI file
```
sudo nano /var/www/catalog/catalog.wsgi
```

- Add following into `catalog.wsgi`
```
#!/usr/bin/python
import sys
import logging
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0,"/var/www/catalog/")

from catalog import app as application
application.secret_key = 'super_secret_key'
```

- Restart Apache
```
sudo service apache2 restart
```

#### 12. Setup PostgreSQL

- Install psql
```
sudo apt-get install postgresql postgresql-contrib
```

- Switch user from `ubuntu` to `postgres` (user `postgres` is automatically created when `psql` is installed)
```
sudo su - postgres
psql
postgres=# CREATE ROLE catalog;
postgres=# ALTER USER catalog WITH PASSWORD 'catalog';
postgres=# ALTER ROLE catalog WITH LOGIN;
postgres=# CREATE DATABASE catalog WITH OWNER catalog;
```

- To check list of all database
`postgres=# \l`

- To check list of all tables in current database
`postgres=# \dt`

- To logout
`postgres=# \q`

#### 13. Modify files to access database

- Search Look `engine = create_engine` in your code base

- Change `sqlite:///sportscategory.db` to `postgresql://catalog:catalog@localhost/catalog`to connect database via user `catalog`

- You should modify three `.py` files:
<img src="https://user-images.githubusercontent.com/6285935/33256427-ffc43008-d38c-11e7-9824-4742b043a855.png" width="100%"></img>

- Add exact oauth file locations in to your code. I made four changes:
`client_secret_google.json` to `/var/www/catalog/catalog/oauth/client_secret_google.json`
`fbclientsecrets.json` to `/var/www/catalog/catalog/oauth/fbclientsecrets.json`

- Create oauth folder and move your oauth files into it.
```
sudo mkdir /var/www/catalog/catalog/oauth
sudo mv /var/www/catalog/catalog/client_secret_google.json /var/www/catalog/catalog/oauth/client_secret_google.json
sudo mv /var/www/catalog/catalog/fbclientsecrets.json /var/www/catalog/catalog/oauth/fbclientsecrets.json
```

#### 14. Make sure both Google and Facebook have correct settings for your AWS IP
**Google**
<img src="https://user-images.githubusercontent.com/6285935/33256204-0de4f4c0-d38c-11e7-9b5b-60451685d4df.png" width="100%"></img>

**Facebook**
<img src="https://user-images.githubusercontent.com/6285935/33253543-d414af7c-d37e-11e7-866d-e4a461772a3b.png" width="100%"></img>

#### 15. Run your application
```
sudo python /var/www/catalog/catalog/__init__.py
```

## Getting Start

1. Open browser of your choice(**Chrome, Firefox, Safari**, etc)
2. Connect to **13.230.63.149**
3. You should be able to see the home page of the catalog website

## Built With
* [Google Login OAuth2](https://developers.google.com/identity/protocols/OAuth2UserAgent)
* [Facebook Login OAuth2](https://developers.facebook.com/docs/facebook-login/web)
* [Amazon Lightsail](https://amazonlightsail.com/)
* [Apache Http Server](https://httpd.apache.org/)
* [Flask](http://flask.pocoo.org/)
* [PostgreSQL](https://www.postgresql.org/docs/9.2/static/app-psql.html)

## Acknowledgements
Here are the refences I've used during this project

* https://stackoverflow.com/questions/35254786/postgresql-role-is-not-permitted-to-log-in

* https://aws.amazon.com/tw/premiumsupport/knowledge-center/new-user-accounts-linux-instance/

* https://www.digitalocean.com/community/tutorials/how-to-deploy-a-flask-application-on-an-ubuntu-vps

* http://flask-cn.readthedocs.io/en/latest/deploying/mod_wsgi/

* https://cloudacademy.com/blog/how-to-set-up-your-first-amazon-lightsail/

* https://github.com/chrisullyott/udacity-fsnd-final

* http://felixhayashi.github.io/ReadmeGalleryCreatorForGitHub/

* https://help.ubuntu.com/community/UFW