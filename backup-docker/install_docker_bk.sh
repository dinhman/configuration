apt update -y
docker --version
rm -rf /usr/local/go && tar -C /usr/local -xzf go1.21.0.linux-amd64.tar.gz
echo export PATH=$PATH:/root/docker-backup/ >> $HOME/.profile
apt install golang-go -y
apt install gccgo-go -y
go version
git clone https://github.com/muesli/docker-backup.git
cd docker-backup
go build
docker-backup --help
docker ps -a
docker-backup backup --tar wordpress-app
ls
docker stop wordpress-app && docker rm wordpress-app
docker-backup restore wordpress-latest-wordpress-app.tar && docker rm wordpress-app
cd /opt/wordpress
docker compose up -d