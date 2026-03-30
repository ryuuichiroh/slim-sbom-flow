# Docker 環境のセットアップ手順書

このドキュメントでは、`docker` / `docker compose` を利用するための環境のセットアップ手順を説明します。

## docker / docker compose のインストール状態の確認

システムを構築するサーバーに、既に docker (docker compose) がインストールされている場合、
docker のインストールは不要です。

docker がインストールされているか、以下のコマンドで確認してください。

```bash
# docker のバージョン確認
docker --version
```

docker がインストールされていれば、`docker compose` も利用できます。
```bash
# docker compose のバージョン確認
docker compose version
```

## docker / docker compose の利用環境のセットアップ

1. 以下のコマンドを実行して docker / docker compose をインストールします

   ```bash
   # Add Docker's official GPG key:
   sudo apt update
   sudo apt install -y ca-certificates curl gnupg
   sudo install -m 0755 -d /etc/apt/keyrings
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
   sudo chmod a+r /etc/apt/keyrings/docker.gpg

   # Add the repository to Apt sources:
   echo \
     "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
     $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
     sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

   sudo apt update

   # Install docker
   sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
   ```
   
2. sudo なしで docker を利用できるようにします
   ```bash   
   sudo usermod -aG docker $USER
   newgrp docker
   ```

3. サーバからログアウトし、ターミナルに再ログインします

4. `docker` および `docker compose` コマンドを実行できるか確認します。
   [docker / docker compose のインストール状態の確認](#docker--docker-compose-のインストール状態の確認)を参照してください。

