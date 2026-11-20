

import socket
import sys


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 client.py <host_servidor> [porta] [usuario] [senha]")
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    user = sys.argv[3] if len(sys.argv) > 3 else input("Usuario: ")
    pwd = sys.argv[4] if len(sys.argv) > 4 else input("Senha: ")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        sock_file = s.makefile("r", encoding="utf-8", newline="\n")

        login_line = f"LOGIN {user} {pwd}\n"
        s.sendall(login_line.encode("utf-8"))
        resp = sock_file.readline().strip()
        print(f"Servidor respondeu: {resp}")

        if resp != "OK LOGIN":
            print("Falha de autenticacao. Encerrando.")
            return

        print("Autenticado. Digite mensagens (ou /quit para sair):")
        while True:
            try:
                texto = input("> ")
            except EOFError:
                break
            if texto.strip() == "/quit":
                s.sendall(b"QUIT\n")
                print(f"Servidor respondeu: {sock_file.readline().strip()}")
                break

            s.sendall(f"MSG {texto}\n".encode("utf-8"))
            resp = sock_file.readline().strip()
            print(f"Servidor respondeu: {resp}")


if __name__ == "__main__":
    main()
