# Interceptacao e Defesa de um Protocolo de Aplicacao

Este projeto implementa as **Fases 1, 2 e 3** do trabalho de Laboratorio de Redes de Computadores:

- Fase 1: escuta passiva e demonstracao de quebra de confidencialidade;
- Fase 2: interceptacao ativa por ARP Spoofing e alteracao controlada de mensagens;
- Fase 3: defesa com TLS, autenticacao do servidor por certificado e protecao das credenciais no servidor.

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

Credenciais de teste definidas no servidor inseguro:

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

## Parte 2 - Interceptacao ativa

Na VM atacante, execute o ARP Spoofing com o IP da VM cliente e da VM servidor:

```bash
sudo python3 src/arp_spoof.py eth0 192.168.56.11 192.168.56.10
```

Com o trafego atraves da VM atacante, o sniffer continua mostrando credenciais e mensagens
em texto claro. Para a evidencia controlada, o proxy legado pode ser usado em paralelo:

```bash
python3 src/proxy.mitm.py 5001 192.168.56.10 5000
```

Depois, aponte o cliente para a porta `5001` da VM proxy:

```bash
python3 client.py 192.168.56.12 5001 alice senha123
```

A classe `proxy.mitm.py` intercepta linhas `MSG`, registra o texto original e substitui
o conteudo por uma mensagem controlada antes de encaminha-lo ao servidor. A sessao
aceita varias conexoes por meio de threads; erros de uma conexao nao encerram o proxy.

## Parte 3 - Defesa

O antes vulneravel usa o protocolo em texto claro e o `client.py` sem validacao
criptografica. O depois protegido usa TLS e pode bloquear a falsificacao ARP por
entradas permanentes.

### Gerar o certificado na VM servidor

Na VM servidor, gere uma Autoridade Certificadora local e um certificado cujo IP
deve corresponder ao IP real do servidor:

Os arquivos necessarios ja foram gerados neste projeto na pasta `certs/` para o IP
`192.168.56.10`. Para regenerar ou adaptar o IP, execute:

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
python3 src/secure_client.py 192.168.56.10 5000 ceci grebbio2027 certs/ca.crt
```

O cliente verifica a cadeia do certificado e o IP servido. Assim, um atacante que
apresente um certificado falso nao sera aceito. O sniffer fara a captura, mas nao
conseguira apresentar credenciais ou mensagens em texto claro.

Os usuarios registrados no servidor TLS sao:

```text
ceci   / grebbio2027
felipe / inter2027
```

As senhas nao ficam armazenadas em texto claro no `secure_server.py`: somente seus
valores SHA-256 sao mantidos em memoria para comparacao do login.

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

### Evidencias antes/depois

Para comprovar a defesa no Wireshark:

1. Capture a porta TCP 5000 antes da TLS.
2. Identifique os pacotes `TCP` que contem `LOGIN`, `MSG` e as respostas `OK LOGIN`/`ACK MSG`.
3. Capture a mesma porta com o servidor e o cliente TLS.
4. Identifique o `Client Hello`, `Server Hello`, o certificado e os registros `Application Data`.
5. Confirme que o conteudo nao aparece em texto claro.
6. Execute novamente o ARP Spoofing e registre o erro de validacao do certificado no cliente.

Capturas recomendadas:

```text
fase1_texto_claro.pcapng
fase2_mitm_texto_claro.pcapng
fase3_tls_sem_mitm.pcapng
fase3_tls_com_mitm.pcapng
```

### Analise da defesa e deteccao

- **Sniffing:** mitigado pela confidencialidade do TLS. Metadados, como IPs, portas e tamanho aproximado dos pacotes, continuam visiveis.
- **MITM por ARP:** mitigado pela autenticacao do servidor e pela integridade da sessao TLS.
- **Adulteracao:** rejeitada pela integridade criptografica. Se houver alteracao em um registro TLS, o handshake ou a conexao sera encerrado.
- **Certificado falso:** detectado no cliente por `SSLCertVerificationError`, por exemplo cadeia nao confiavel, IP/hostname divergente ou certificado expirado.
- **Replay:** TLS inclui protecoes contra repeticao de registros; o trabalho nao implementa uma politica explicita de expiracao das credenciais ou nonce em nivel de aplicacao.
- **Ataques fora do escopo:** TLS nao protege contra malware na VM cliente/servidor, roubo da chave privada, pessoa maliciosa autorizada ou vazamento dos dados antes da criptografia.

### Limites da prova

A configuracao usa uma Autoridade Certificadora local para o laboratorio. Em producao,
o certificado deveria ser emitido por uma Autoridade confiavel ou distribuido por um
processo seguro. O modo X509 estrito foi desabilitado no cliente somente para compatibilidade
com o ambiente da VM; a cadeia, o hostname/IP e o TLS 1.2 continuam sendo validados.

