

import socket
import sys
import threading
from datetime import datetime

# "Base de usuários" em texto claro de propósito -- isso é o alvo da
# demonstração de vulnerabilidade. NÃO fazer isso em sistema real.
USERS = {
    "alice": "senha123",
    "bob": "trocar@2026",
}

HOST = sys.argv[1] if len(sys.argv) > 1 else "0.0.0.0"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 5000


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def handle_client(conn, addr):
    log(f"Conexao de {addr}")
    authenticated_user = None
    buffer = ""
    try:
        with conn:
            conn_file = conn.makefile("r", encoding="utf-8", newline="\n")
            while True:
                line = conn_file.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue

                log(f"[{addr}] RECEBIDO: {line}")

                parts = line.split(" ", 1)
                cmd = parts[0].upper()

                if cmd == "LOGIN":
                    # Formato: LOGIN usuario senha
                    args = parts[1].split(" ", 1) if len(parts) > 1 else []
                    if len(args) == 2:
                        user, pwd = args
                        if USERS.get(user) == pwd:
                            authenticated_user = user
                            conn.sendall(b"OK LOGIN\n")
                            log(f"[{addr}] LOGIN OK para usuario '{user}'")
                        else:
                            conn.sendall(b"FAIL LOGIN\n")
                            log(f"[{addr}] LOGIN FALHOU para usuario '{user}'")
                    else:
                        conn.sendall(b"FAIL LOGIN\n")

                elif cmd == "MSG":
                    texto = parts[1] if len(parts) > 1 else ""
                    if authenticated_user:
                        log(f"[{addr}] MSG de '{authenticated_user}': {texto}")
                        conn.sendall(b"ACK MSG\n")
                    else:
                        conn.sendall(b"FAIL NOT_AUTHENTICATED\n")

                elif cmd == "QUIT":
                    conn.sendall(b"BYE\n")
                    break

                else:
                    conn.sendall(b"FAIL UNKNOWN_CMD\n")

    except ConnectionResetError:
        pass
    finally:
        log(f"Conexao encerrada: {addr}")


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(5)
        log(f"Servidor escutando em {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()


if __name__ == "__main__":
    main()
