import socket
import sys
import threading

def handle_client_to_server(client_socket, server_socket, client_addr):
    """Lê as mensagens do cliente, modifica se necessário, e envia ao servidor."""
    try:
        client_file = client_socket.makefile("r", encoding="utf-8", newline="\n")
        while True:
            line = client_file.readline()
            if not line:
                break
            
            if line.startswith("MSG "):
                print(f"[MITM - {client_addr}] Mensagem original interceptada: {line.strip()}")
                line = "MSG O proxy MITM interceptou e alterou esta mensagem!\n"
                print(f"[MITM - {client_addr}] Mensagem modificada para: {line.strip()}")

            server_socket.sendall(line.encode("utf-8"))
    except Exception as e:
        print(f"[MITM - {client_addr}] Erro na rota Cliente->Servidor: {e}")
    finally:
        server_socket.close()
        client_socket.close()

def handle_server_to_client(server_socket, client_socket, client_addr):
    """Lê as respostas do servidor e repassa intactas para o cliente."""
    try:
        server_file = server_socket.makefile("r", encoding="utf-8", newline="\n")
        while True:
            line = server_file.readline()
            if not line:
                break
            
            client_socket.sendall(line.encode("utf-8"))
    except Exception as e:
        pass 
    finally:
        server_socket.close()
        client_socket.close()

def handle_connection(client_socket, client_addr, server_host, server_port):
    """Gerencia uma nova conexão criando a ponte com o servidor real."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        server_socket.connect((server_host, server_port))
        print(f"[MITM] Ponte estabelecida entre {client_addr} e Servidor {server_host}:{server_port}")

        t1 = threading.Thread(target=handle_client_to_server, args=(client_socket, server_socket, client_addr), daemon=True)
        t2 = threading.Thread(target=handle_server_to_client, args=(server_socket, client_socket, client_addr), daemon=True)
        
        t1.start()
        t2.start()
    except Exception as e:
        print(f"[MITM] Falha ao conectar no servidor real para {client_addr}: {e}")
        client_socket.close()

def main():
    if len(sys.argv) < 3:
        print("Uso: python3 proxy_mitm.py <porta_local> <host_servidor_real> [porta_servidor_real]")
        sys.exit(1)

    local_port = int(sys.argv[1])
    server_host = sys.argv[2]
    server_port = int(sys.argv[3]) if len(sys.argv) > 3 else 5000

    proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    proxy.bind(("0.0.0.0", local_port))
    proxy.listen(5)
    
    print(f"[MITM] Proxy escutando na porta {local_port} e redirecionando para {server_host}:{server_port}")

    while True:
        try:
            client_sock, addr = proxy.accept()
            print(f"[MITM] Nova conexão recebida de {addr}")
            t = threading.Thread(target=handle_connection, args=(client_sock, addr, server_host, server_port), daemon=True)
            t.start()
        except KeyboardInterrupt:
            print("\n[MITM] Encerrando proxy.")
            break

if __name__ == "__main__":
    main()