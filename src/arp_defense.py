import argparse
import subprocess
import sys


def run_ip(*arguments):
    subprocess.run(["ip", "neigh", *arguments], check=True)


def main():
    parser = argparse.ArgumentParser(
        description="Configura uma entrada ARP permanente no laboratorio."
    )
    parser.add_argument("interface", help="Interface de rede, por exemplo: eth0")
    parser.add_argument("ip_address", help="Endereco IP protegido")
    parser.add_argument("mac_address", help="MAC real do endereco IP")
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove a entrada permanente",
    )
    args = parser.parse_args()

    if sys.platform != "linux":
        print("ERRO: execute este script em uma VM Linux.")
        sys.exit(1)

    try:
        if args.remove:
            run_ip(
                "del",
                args.ip_address,
                "dev",
                args.interface,
            )
            print(f"Entrada ARP removida: {args.ip_address}")
        else:
            run_ip(
                "replace",
                args.ip_address,
                "lladdr",
                args.mac_address,
                "nud",
                "permanent",
                "dev",
                args.interface,
            )
            print(
                f"Entrada ARP permanente configurada: "
                f"{args.ip_address} -> {args.mac_address}"
            )
    except FileNotFoundError:
        print("ERRO: utilitario 'ip' nao encontrado.")
        sys.exit(1)
    except subprocess.CalledProcessError as error:
        print(f"ERRO ao configurar a entrada ARP: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
