from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import paramiko
import uuid
import time
import shlex
import re

app = FastAPI()

# セッションを保存する辞書
ssh_sessions = {}

# セッション情報の構造
class SSHSession:
    def __init__(self, ssh_client, password, creation_time):
        self.ssh_client = ssh_client
        self.password = password
        self.creation_time = creation_time

class ConnectionData(BaseModel):
    host: str
    username: str
    password: str

class CommandData(BaseModel):
    session_id: str
    command: str

class SaveFileData(BaseModel):
    session_id: str
    file_path: str
    content: str
    use_sudo: bool = False  # sudoを使用するかどうかのオプション

class CloseSessionData(BaseModel):
    session_id: str

@app.post("/connect/")
async def connect(data: ConnectionData):
    try:
        # SSHクライアントの初期化
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname=data.host, username=data.username, password=data.password)
        
        # セッションIDを生成し、セッションを保存
        session_id = str(uuid.uuid4())
        ssh_sessions[session_id] = SSHSession(ssh, data.password, time.time())
        
        return {"session_id": session_id, "message": "Connected successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/execute/")
async def execute(data: CommandData):
    session = ssh_sessions.get(data.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # `nano`、`vim`、`vi`のコマンドをキャッチしてファイル内容を返す処理
        if re.match(r'(nano|vim|vi) ', data.command):
            # コマンドからファイルパスを抽出しcatで内容を取得
            file_path = data.command.split()[-1]
            command = f"cat {shlex.quote(file_path)}"
            
            stdin, stdout, stderr = session.ssh_client.exec_command(command)
            file_content = stdout.read().decode()
            error = stderr.read().decode()
            if error:
                raise HTTPException(status_code=500, detail=error)
            
            # ファイル内容を返す
            return {"file_path": file_path, "file_content": file_content}

        # `sudo apt`コマンドの特別な処理
        if "sudo apt" in data.command:
            command = f"echo '{session.password}' | sudo -S DEBIAN_FRONTEND=noninteractive {data.command.split('sudo ')[-1]}"
        elif "sudo" in data.command:
            # 一般的なsudoコマンド処理
            command = f"echo '{session.password}' | sudo -S {data.command.split('sudo ')[-1]}"
        else:
            command = data.command
        
        stdin, stdout, stderr = session.ssh_client.exec_command(command)
        stdin.write(session.password + '\n')
        stdin.flush()
        output = stdout.read().decode()
        error = stderr.read().decode()

        # 警告メッセージが含まれていてもエラーとせず出力を返す
        if error and "WARNING" in error:
            return {"output": output, "warning": error}
        elif error:
            raise HTTPException(status_code=500, detail=error)

        return {"output": output}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/save_file/")
async def save_file(data: SaveFileData):
    session = ssh_sessions.get(data.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        # ファイル内容を直接書き込むコマンドを構築
        safe_content = data.content.replace('"', '\\"')
        if data.use_sudo:
            command = f"echo \"{safe_content}\" | sudo -S tee {shlex.quote(data.file_path)}"
        else:
            command = f"echo \"{safe_content}\" > {shlex.quote(data.file_path)}"

        stdin, stdout, stderr = session.ssh_client.exec_command(command)
        stdin.write(session.password + '\n')
        stdin.flush()
        output = stdout.read().decode()
        error = stderr.read().decode()
        if error:
            raise HTTPException(status_code=500, detail=error)

        return {"message": "File content replaced successfully", "output": output}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/close/")
async def close(data: CloseSessionData):
    session = ssh_sessions.pop(data.session_id, None)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        session.ssh_client.close()
        return {"message": "Connection closed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 不要なセッションを自動的にクリーンアップする関数
def cleanup_sessions(max_age=3600):
    current_time = time.time()
    expired_sessions = [sid for sid, sess in ssh_sessions.items() if current_time - sess.creation_time > max_age]
    for sid in expired_sessions:
        try:
            ssh_sessions[sid].ssh_client.close()
        except Exception as e:
            print(f"Failed to close session {sid}: {str(e)}")
        ssh_sessions.pop(sid, None)

if __name__ == "__main__":
    import uvicorn
    import threading

    # 定期的にセッションをクリーンアップするスレッドを開始
    def session_cleanup_thread():
        while True:
            cleanup_sessions()
            time.sleep(600)  # 10分ごとにクリーンアップを実行

    threading.Thread(target=session_cleanup_thread, daemon=True).start()
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
