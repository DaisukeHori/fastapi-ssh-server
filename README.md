# FastAPI SSH Server

このプロジェクトは、FastAPIを使用してSSH接続を管理するサーバーアプリケーションです。ユーザーは、REST API経由でSSHセッションを開始し、コマンドを実行したり、ファイルを操作したりできます。

LLMやIPaaSでサーバーのキッティングやメンテナンスを自動化させるためのものとして想定しています。

## 前提条件

このプロジェクトを実行するには、以下のソフトウェアがインストールされている必要があります。

- Docker
- Git
- Python 3.9 以上

## セットアップ手順

### 1. リポジトリのクローン

まず、GitHubリポジトリからプロジェクトをクローンします。

```bash
git clone https://github.com/DaisukeHori/fastapi-ssh-server.git
cd fastapi-ssh-server
```

### 2. Dockerイメージのビルド

プロジェクトディレクトリに移動し、Dockerイメージをビルドします。

```bash
docker build -t fastapi-ssh-server .
```

### 3. Dockerコンテナの起動

ビルドが完了したら、以下のコマンドでDockerコンテナを起動します。

```bash
docker run -d -p 8000:8000 fastapi-ssh-server
```

これで、FastAPIサーバーが起動し、ポート8000でリクエストを受け付けるようになります。

### 4. APIの使用

以下のステップに従ってAPIを使用します。

#### 4.1 SSHセッションの開始

最初に、`/connect`エンドポイントにPOSTリクエストを送信して、SSH接続を確立します。以下は、例です。

```bash
curl -X POST "http://localhost:8000/connect/" -H "Content-Type: application/json" -d '{
    "host": "example.com",
    "username": "your_username",
    "password": "your_password"
}'
```

成功すると、`session_id`が返されます。この`session_id`を使って、以降のリクエストを行います。

#### 4.2 コマンドの実行

`/execute`エンドポイントにPOSTリクエストを送信して、SSHセッション内でコマンドを実行します。

```bash
curl -X POST "http://localhost:8000/execute/" -H "Content-Type: application/json" -d '{
    "session_id": "your_session_id",
    "command": "ls -la"
}'
```

このリクエストは、指定したコマンドの出力を返します。

#### 4.3 ファイルの保存

`/save_file`エンドポイントを使用して、サーバー上のファイルを編集または保存できます。

```bash
curl -X POST "http://localhost:8000/save_file/" -H "Content-Type: application/json" -d '{
    "session_id": "your_session_id",
    "file_path": "/path/to/your/file.txt",
    "content": "新しいファイルの内容",
    "use_sudo": true
}'
```

このリクエストは、指定したファイルに内容を書き込みます。

#### 4.4 SSHセッションの終了

作業が完了したら、`/close`エンドポイントを使用してSSHセッションを終了します。

```bash
curl -X POST "http://localhost:8000/close/" -H "Content-Type: application/json" -d '{
    "session_id": "your_session_id"
}'
```

これで、セッションがクローズされます。

### 5. APIドキュメントの確認

FastAPIは、提供するAPIのインタラクティブなドキュメントを自動生成します。以下のURLにアクセスして、Swagger UIからAPIを試すことができます。

```
http://localhost:8000/docs
```

## 注意点

- SSH接続のセキュリティには十分注意してください。公開されるサーバーの場合、IPフィルタリングやファイアウォールなどでアクセスを制限することをお勧めします。
- このプロジェクトは教育目的や実験的な使用を想定しており、商用環境での使用には十分なセキュリティ対策が必要です。

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。
