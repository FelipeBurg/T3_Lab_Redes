import socket
import ssl
import sys
import threading
import hashlib
from datetime import datetime

USERS = {
    "ceci": hashlib.sha256("grebbio2027".encode()).hexdigest(),
    "felipe": hashlib.sha256("inter2027".encode()).hexdigest(),
}

HOST = sys.argv[1] if len(sys.argv) > 1 else "0.0.0.0"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
CERT_FILE = sys.argv[3] if len(sys.argv) > 3 else "certs/server.crt"
KEY_FILE = sys.argv[4] if len(sys.argv) > 4 else "certs/server.key"


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def handle_client(conn, addr):
    log(f"Conexao TLS de {addr}")
    authenticated_user = None

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

                log(f"[{addr}] COMANDO RECEBIDO POR TLS: {line.split(' ', 1)[0]}")
                parts = line.split(" ", 1)
                cmd = parts[0].upper()

                if cmd == "LOGIN":
                    args = parts[1].split(" ", 1) if len(parts) > 1 else []
                    if len(args) == 2:
                        user, pwd = args
                        pwd_hash = hashlib.sha256(pwd.encode("utf-8")).hexdigest()
                        if USERS.get(user) == pwd_hash:
                            authenticated_user = user
                            conn.sendall(b"OK LOGIN\n")
                            log(f"[{addr}] LOGIN OK para usuario '{user}'")
                        else:
                            conn.sendall(b"FAIL LOGIN\n")
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
    except ssl.SSLError as error:
        log(f"Erro TLS na conexao de {addr}: {error}")
    except ConnectionResetError:
        pass
    finally:
        log(f"Conexao encerrada: {addr}")


def main():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(CERT_FILE, KEY_FILE)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        log(f"Servidor TLS escutando em {HOST}:{PORT}")

        while True:
            raw_conn, addr = server_socket.accept()
            try:
                tls_conn = context.wrap_socket(raw_conn, server_side=True)
                thread = threading.Thread(
                    target=handle_client,
                    args=(tls_conn, addr),
                    daemon=True,
                )
                thread.start()
            except ssl.SSLError as error:
                log(f"Falha no handshake TLS de {addr}: {error}")
                raw_conn.close()


if __name__ == "__main__":
    main()
