# Interceptacao e Defesa de um Protocolo de Aplicacao

Este projeto implementa as **Fases 1 e 2** do trabalho de Laboratorio de Redes de Computadores. A Fase 1 aborda a escuta passiva (sniffer), enquanto a Fase 2 aborda a interceptacao ativa por meio de ARP Spoofing.

- um cliente e um servidor de chat simples;
- um protocolo de aplicacao em texto claro;
- um sniffer passivo implementado diretamente com sockets raw;
- uma demonstracao de que credenciais e mensagens podem ser lidas durante o transito.
- uma demonstracao ativa com ARP Spoofing para que trafego entre cliente e servidor passe pela VM atacante.

O uso deve ser restrito ao laboratorio isolado do grupo.

## Topologia

Use pelo menos tres VMs Linux conectadas a uma rede interna ou host-only comum:

```text
+------------------+       rede isolada       +------------------+
| VM Cliente       |<------------------------>| VM Servidor      |
| client.py        |       TCP/5000           | server.py        |
| IP: 192.168.56.11|                          | IP: 192.168.56.10|
+------------------+                          +------------------+
          |                                             |
          |               trafego roteado               |
          |                                             |
+------------------+
| VM Atacante      |
| arp_spoof.py     |
| sniffer.py       |
| IP: 192.168.56.12|
+------------------+
```

A VM atacante envenena as tabelas ARP do cliente e do servidor. A captura pode ser
executada na propria VM atacante porque o trafego cruza sua interface enquanto
e encaminhado pelo kernel.

## Requisitos

- Python 3 em todas as VMs;
- Linux nas tres VMs;
- privilegios de root na VM atacante;
- cliente e servidor na mesma rede isolada;
- porta TCP 5000 liberada entre cliente e servidor.

## Arquivos

- `server.py`: servidor do protocolo `SimpleChat`.
- `client.py`: cliente que realiza login e envia mensagens.
- `sniffer.py`: captura e interpreta pacotes Ethernet, IPv4 e TCP.
- `arp_spoof.py`: realiza o ataque MITM por ARP Spoofing.
- `proxy.mitm.py`: legado da versao anterior; nao e necessario para a fase com ARP.
- `secure_server.py`: versao TLS da fase de defesa.
- `secure_client.py`: cliente TLS que verifica o certificado do servidor.
- `arp_defense.py`: configura ou remove uma entrada ARP permanente.

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

### 2. Iniciar o ARP Spoofing na VM atacante

Na VM atacante, execute como root. Substitua `eth0` pelo nome da interface conectada a rede isolada:

```bash
sudo pip3 install -r requirements.txt
sudo python3 src/arp_spoof.py eth0 192.168.56.11 192.168.56.10
```

Saida esperada:

```text
ARP spoofing iniciado: 192.168.56.11 <-> 192.168.56.10 atraves de <MAC-atacante>
Pressione Ctrl+C para restaurar as tabelas ARP.
```

Essa VM ativa temporariamente o encaminhamento IPv4 e envia respostas ARP falsas:

- para o cliente: afirma que o IP do servidor pertence ao MAC da VM atacante;
- para o servidor: afirma que o IP do cliente pertence ao MAC da VM atacante.

### 3. Iniciar o sniffer na VM atacante

Em outro terminal da VM atacante:

```bash
sudo python3 src/sniffer.py eth0 5000
```

Saida esperada:

```text
Sniffer iniciado na interface 'eth0', filtrando porta 5000
Aguardando trafego do protocolo alvo... (Ctrl+C para parar)
```

### 4. Iniciar o cliente

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

Ao pressionar `Ctrl+C`, o script envia pacotes ARP reais e desativa o encaminhamento
IP, restaurando o caminho normal da rede.

## Parte 3 - Defesa

O antes vulneravel usa o protocolo em texto claro e o `client.py` sem validacao
criptografica. O depois protegido usa TLS e pode bloquear a falsificacao ARP por
entradas permanentes.

### Gerar o certificado na VM servidor

Na VM servidor, gere uma Autoridade Certificadora local e um certificado cujo IP
deve corresponder ao IP real do servidor:

```bash
mkdir -p certs
openssl genrsa -out certs/ca.key 4096
openssl req -x509 -new -nodes -key certs/ca.key \
  -sha256 -days 365 -out certs/ca.crt \
  -subj "/CN=SimpleChat-Lab-CA"

openssl genrsa -out certs/server.key 2048
openssl req -new -key certs/server.key -out certs/server.csr \
  -subj "/CN=192.168.56.10"

cat > certs/server.ext <<'EOF'
subjectAltName=IP:192.168.56.10
extendedKeyUsage=serverAuth
EOF

openssl x509 -req -in certs/server.csr \
  -CA certs/ca.crt -CAkey certs/ca.key -CAcreateserial \
  -out certs/server.crt -days 365 -sha256 \
  -extfile certs/server.ext
```

Copie `certs/ca.crt` para a VM cliente. O arquivo `server.key` permanece secreto na
VM servidor.

### Executar o servidor protegido

Na VM servidor:

```bash
python3 src/secure_server.py 0.0.0.0 5000 \
  certs/server.crt certs/server.key
```

Na VM cliente:

```bash
python3 src/secure_client.py 192.168.56.10 5000 alice senha123 certs/ca.crt
```

O cliente verifica a cadeia do certificado e o IP servido. Assim, um atacante que
apresente um certificado falso nao sera aceito. O sniffer fara a captura, mas nao
conseguira apresentar credenciais ou mensagens em texto claro.

### Defesa adicional contra ARP Spoofing

Antes do teste, obtenha o MAC real da VM servidor:

```bash
ip neigh show 192.168.56.10
```

E do cliente:

```bash
ip neigh show 192.168.56.11
```

Configure as entradas permanentes em cada VM cliente/servidor:

```bash
# Na VM cliente
sudo python3 src/arp_defense.py eth0 192.168.56.10 AA:BB:CC:DD:EE:FF

# Na VM servidor
sudo python3 src/arp_defense.py eth0 192.168.56.11 11:22:33:44:55:66
```

Substitua os MACs pelos valores reais. Para remover as entradas ao final:

```bash
sudo python3 src/arp_defense.py eth0 192.168.56.10 AA:BB:CC:DD:EE:FF --remove
```

Para documentar a defesa no relatorio, execute novamente o ataque e compare:

1. Antes: o sniffer mostra `LOGIN usuario senha` e `MSG mensagem`.
2. Depois: o sniffer mostra apenas pacotes TLS/Handshake; o proxy nao decodifica
   nem modifica o conteudo.
3. Com entradas ARP permanentes: os pacotes falsos do atacante sao ignorados.

