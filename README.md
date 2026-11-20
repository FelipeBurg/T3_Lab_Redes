# Interceptacao e Defesa de um Protocolo de Aplicacao

Este projeto implementa as **Fases 1 e 2** do trabalho de Laboratorio de Redes de Computadores. A Fase 1 aborda a escuta passiva (sniffer), enquanto a Fase 2 (mais pro meio do documento) aborda a interceptação ativa via proxy MITM.

- um cliente e um servidor de chat simples;
- um protocolo de aplicacao em texto claro;
- um sniffer passivo implementado diretamente com sockets raw;
- uma demonstracao de que credenciais e mensagens podem ser lidas durante o transito.

O uso deve ser restrito ao laboratorio isolado do grupo.

## Topologia

Use pelo menos tres VMs Linux conectadas a uma rede interna ou host-only comum:

```text
+------------------+       rede isolada       +------------------+
| VM Cliente       |--------------------------| VM Servidor      |
| client.py        |        TCP/5000          | server.py        |
| IP: 192.168.56.11|                          | IP: 192.168.56.10|
+------------------+                          +------------------+
          |                                             |
          |       trafego visivel por espelhamento       |
          +----------------------+----------------------+
                                 |
                         +------------------+
                         | VM Observadora   |
                         | sniffer.py       |
                         | IP: 192.168.56.12|
                         +------------------+
```

A VM observadora precisa receber os pacotes entre cliente e servidor. Em uma rede com switch virtual, configure uma destas alternativas:

1. espelhamento de porta (port mirroring);
2. modo promiscuo permitido no adaptador virtual;
3. hub virtual ou outro mecanismo equivalente de laboratorio.

No Linux, o modo promiscuo da interface pode ser ativado com:

```bash
sudo ip link set eth0 promisc on
```

Confirme o nome real da interface com:

```bash
ip link
```

Uma rede NAT comum pode impedir que a VM observadora veja o trafego unicast das outras VMs.

## Requisitos

- Python 3 em todas as VMs;
- Linux ou Windows na VM observadora;
- privilegios de root no Linux ou PowerShell como Administrador no Windows;
- cliente e servidor na mesma rede isolada;
- porta TCP 5000 liberada entre cliente e servidor.

## Arquivos

- `server.py`: servidor do protocolo `SimpleChat`.
- `client.py`: cliente que realiza login e envia mensagens.
- `sniffer.py`: captura e interpreta pacotes Ethernet, IPv4 e TCP.

## Protocolo em texto claro

Mensagens enviadas pelo cliente:

```text
LOGIN <usuario> <senha>\n
MSG <mensagem>\n
QUIT\n
```

Respostas do servidor:

```text
OK LOGIN\n
FAIL LOGIN\n
ACK MSG\n
BYE\n
```

Credenciais de teste definidas no servidor:

```text
alice / senha123
bob   / trocar@2026
```

## Execucao

### 1. Iniciar o servidor

Na VM servidor, descubra o endereco IP da interface da rede isolada e execute:

```bash
python3 server.py 0.0.0.0 5000
```

Saida esperada:

```text
Servidor escutando em 0.0.0.0:5000
```

### 2. Iniciar o sniffer no Linux

Na VM observadora, execute como root. Substitua `eth0` pelo nome da interface conectada a rede isolada:

```bash
sudo python3 sniffer.py eth0 5000
```

Saida esperada:

```text
Sniffer iniciado na interface 'eth0', filtrando porta 5000
Aguardando trafego do protocolo alvo... (Ctrl+C para parar)
```

No Windows, abra o PowerShell como Administrador. Informe o IP da interface
da VM observadora, em vez do nome `eth0`:

```powershell
python sniffer.py 192.168.56.12 5000
```

O Windows usa `SIO_RCVALL` para receber pacotes IPv4 pelo socket raw. O
adaptador virtual ainda precisa estar configurado para permitir a captura do
trafego da rede isolada.

### 3. Iniciar o cliente

Na VM cliente, substitua o IP pelo endereco da VM servidor:

```bash
python3 client.py 192.168.56.10 5000 alice senha123
```

Digite uma mensagem, por exemplo:

```text
mensagem secreta da fase 1
```

Digite `/quit` para encerrar.

O sniffer deve mostrar eventos semelhantes a:

```text
*** CREDENCIAIS CAPTURADAS *** usuario='alice' senha='senha123'
*** MENSAGEM CAPTURADA *** 'mensagem secreta da fase 1'
```

