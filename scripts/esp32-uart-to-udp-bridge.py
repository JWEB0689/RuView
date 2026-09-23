#!/usr/bin/env python3
"""
esp32-uart-to-udp-bridge.py
Bridge serial UART CSI frames from an ESP32 node to a Cognitum Seed / RuView aggregator over UDP.

Usage:
    python scripts/esp32-uart-to-udp-bridge.py --port /dev/cu.usbserial-0001 --seed 169.254.42.1
    python scripts/esp32-uart-to-udp-bridge.py --port COM3 --seed 169.254.42.1 --udp-port 5005
"""

import argparse
import glob
import os
import re
import socket
import sys
import time

try:
    import serial
except ImportError:
    print("[ERROR] pyserial is required. Install via: pip install pyserial")
    sys.exit(1)

MAGIC_CSI_RAW  = 0xC5110001
MAGIC_VITALS   = 0xC5110002
MAGIC_FEATURES = 0xC5110003

TICK_RE = re.compile(
    r"adaptive_ctrl:\s*\w+\s+tick:\s*"
    r"state=(?P<state>\d+)\s+"
    r"yield=(?P<yield>\d+)pps\s+"
    r"motion=(?P<motion>[\d.]+)\s+"
    r"presence=(?P<presence>[\d.]+)\s+"
    r"rssi=(?P<rssi>-?\d+)"
)

def auto_detect_port():
    if sys.platform.startswith("darwin"):
        ports = glob.glob("/dev/cu.usbserial*") + glob.glob("/dev/cu.usbmodem*")
        if ports:
            return ports[0]
    elif sys.platform.startswith("linux"):
        ports = glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*")
        if ports:
            return ports[0]
    elif sys.platform.startswith("win"):
        return "COM3"
    return "/dev/cu.usbserial-0001"

def resolve_target_seed(seed_host):
    # Try resolving seed_host. If 169.254.42.1 is specified but unreachable,
    # fallback to 127.0.0.1 with an informative notice.
    try:
        addr = socket.gethostbyname(seed_host)
        return addr
    except Exception:
        print(f"[WARN] Could not resolve '{seed_host}'. Defaulting to localhost (127.0.0.1)")
        return "127.0.0.1"

def main():
    parser = argparse.ArgumentParser(description="ESP32 UART to UDP Bridge for Cognitum Seed")
    parser.add_argument("--port", default=auto_detect_port(), help="ESP32 serial port (e.g. /dev/cu.usbserial-0001, COM3)")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate (default: 115200)")
    parser.add_argument("--seed", default="169.254.42.1", help="Target Seed host or IP (default: 169.254.42.1)")
    parser.add_argument("--udp-port", type=int, default=5005, help="Target UDP port (default: 5005)")
    args = parser.parse_args()

    seed_ip = resolve_target_seed(args.seed)
    udp_target = (seed_ip, args.udp_port)

    print(f"==================================================")
    print(f"  Cognitum Seed / RuView ESP32 UART Bridge")
    print(f"==================================================")
    print(f"  Serial Port:   {args.port} @ {args.baud} baud")
    print(f"  Target Seed:   {args.seed} ({seed_ip}):{args.udp_port}")
    print(f"==================================================")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        ser = serial.Serial(args.port, args.baud, timeout=1.0)
    except serial.SerialException as e:
        print(f"\n[!] Notice: Could not open {args.port}: {e}")
        print(f"    If the ESP32 is already provisioned and streaming CSI over Wi-Fi directly")
        print(f"    to UDP 5005, serial bridging is not required — the Seed receives packets over the air!")
        return

    print(f"[✓] Serial port opened. Forwarding frames to {seed_ip}:{args.udp_port}...")
    packet_count = 0
    start_time = time.time()
    last_stat_time = start_time

    buf = bytearray()
    try:
        while True:
            chunk = ser.read(ser.in_waiting or 1)
            if chunk:
                buf.extend(chunk)

                # Look for magic numbers or line endings
                while len(buf) >= 4:
                    # Check for 32-byte vitals or 48-byte feature or raw packets
                    magic = int.from_bytes(buf[:4], byteorder='little')
                    if magic in (MAGIC_CSI_RAW, MAGIC_VITALS, MAGIC_FEATURES):
                        pkt_len = 32 if magic == MAGIC_VITALS else (48 if magic == MAGIC_FEATURES else 128)
                        if len(buf) >= pkt_len:
                            pkt = bytes(buf[:pkt_len])
                            sock.sendto(pkt, udp_target)
                            packet_count += 1
                            del buf[:pkt_len]
                            continue
                        else:
                            break
                    elif b"\n" in buf:
                        line_idx = buf.index(b"\n")
                        line = buf[:line_idx].decode("utf-8", errors="ignore").strip()
                        del buf[:line_idx + 1]

                        if "adaptive_ctrl" in line or "csi" in line.lower():
                            sock.sendto(line.encode("utf-8"), udp_target)
                            packet_count += 1
                    else:
                        # Scan forward for next possible sync
                        del buf[0]

            now = time.time()
            if now - last_stat_time >= 3.0:
                elapsed = now - start_time
                pps = packet_count / (now - last_stat_time) if elapsed > 0 else 0
                print(f"  [STREAMING] Forwarded {packet_count} packets ({pps:.1f} pps) to {seed_ip}:{args.udp_port}")
                last_stat_time = now

    except KeyboardInterrupt:
        print(f"\nBridge stopped by user. Total packets forwarded: {packet_count}")
    finally:
        ser.close()
        sock.close()

if __name__ == "__main__":
    main()
