import socket
import ssl
import sys


def main():
    if len(sys.argv) < 3:
        print(
            "Uso: python3 secure_client.py <host_servidor> "
            "[porta] [usuario] [senha] [ca.crt]"
        )
        sys.exit(1)

    host = sys.argv[1]
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    user = sys.argv[3] if len(sys.argv) > 3 else input("Usuario: ")
    pwd = sys.argv[4] if len(sys.argv) > 4 else input("Senha: ")
    ca_file = sys.argv[5] if len(sys.argv) > 5 else "certs/ca.crt"

    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=ca_file)
    context.minimum_version = ssl.TLSVersion.TLSv1_2

    with socket.create_connection((host, port), timeout=10) as raw_socket:
        with context.wrap_socket(raw_socket, server_hostname=host) as tls_socket:
            tls_socket.sendall(f"LOGIN {user} {pwd}\n".encode("utf-8"))
            with tls_socket.makefile(
                "r", encoding="utf-8", newline="\n"
            ) as sock_file:
                response = sock_file.readline().strip()
                print(f"Servidor respondeu: {response}")

                if response != "OK LOGIN":
                    print("Falha de autenticacao. Encerrando.")
                    return

                print("Autenticado. Digite mensagens (ou /quit para sair):")
                while True:
                    try:
                        texto = input("> ")
                    except EOFError:
                        break

                    if texto.strip() == "/quit":
                        tls_socket.sendall(b"QUIT\n")
                        print(f"Servidor respondeu: {sock_file.readline().strip()}")
                        break

                    tls_socket.sendall(f"MSG {texto}\n".encode("utf-8"))
                    response = sock_file.readline().strip()
                    print(f"Servidor respondeu: {response}")


if __name__ == "__main__":
    try:
        main()
    except ssl.SSLCertVerificationError as error:
        print(f"ERRO: certificado do servidor invalido: {error}")
        sys.exit(1)
    except ssl.SSLError as error:
        print(f"ERRO TLS: {error}")
        sys.exit(1)
