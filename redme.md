py -m venv .venv

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

.\.venv\Scripts\Activate.ps1

deactivate

cloudflared tunnel --url http://127.0.0.1:5000