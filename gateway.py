import json
import re
import socket
import threading
import typing

from drone import Commands as DroneCommands
from client import Commands as ClientCommands

from rich.console import Console

from utils import get_command

console = Console()

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    client_socket.bind(("localhost", 8810))
except OSError as e:
    console.print("Can't open connection with client. Close the previously connected clients before starting gateway.",
                  style="red")
    exit(1)
client_socket.listen(1)

drones_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
drones_socket.bind(("localhost", 8811))

console.log("Waiting client and drones...")


class Drone:
    available = True
    ip: str
    id: str
    addr: tuple

    def __init__(self, ip: str, id: str, addr: tuple):
        self.ip = ip
        self.id = id
        self.addr = addr


drones: dict[str, Drone] = {}


def wait_drones():
    while True:
        data, addr = drones_socket.recvfrom(1024)
        command, *arguments = get_command(data)
        drone_ip = arguments[0]
        match command:
            case DroneCommands.READY.value:
                drone_id = arguments[1]
                if drone_ip not in drones or not drones[drone_ip].available:
                    drone = Drone(drone_ip, drone_id, addr)
                    drone.available = True
                    drones[drone_ip] = drone
                    console.log(f"Drone {drone_id} ({drone_ip}) is ready")
                    drones_socket.sendto(DroneCommands.CONFIRMED.value.encode(), addr)
                else:
                    console.log(f"Rejecting new drone since drone with IP {drone_ip} is already connected.",
                                style="magenta")
                    drones_socket.sendto(DroneCommands.ALREADY_CONNECTED.value.encode(), addr)
            case DroneCommands.DELIVERED.value:
                console.log(f"Drone {drone_ip} delivered the package. Notifying client ({client_ip})...")
                drones[drone_ip].available = True
                client.send(f"{ClientCommands.DRONE_DELIVERED} {drone_ip}".encode())
            case DroneCommands.CONNECTION_CLOSED.value:
                console.log(f"Drone {drone_ip} disconnected")
                if drone_ip in drones:
                    drones[drone_ip].available = False
                    drones[drone_ip].addr = None


def wait_client():
    client, addr = client_socket.accept()
    console.log(f"Client connected!")
    return client, addr


t = threading.Thread(target=wait_drones, daemon=True)
t.start()

client: typing.Union[socket.socket | None] = None
client_ip: typing.Union[str | None] = None

try:
    client, addr = wait_client()
    while True:
        try:
            data = client.recv(1024)
            msg = data.decode()
            if msg == "":
                raise ConnectionResetError()
        except ConnectionResetError:
            console.log("Client disconnected. Waiting for a new one")
            client, addr = wait_client()
            # Client disconnected
            continue

        command, *arguments = get_command(msg)

        match command:
            case ClientCommands.HELLO.value:
                client_ip = arguments[0]
                console.log(f"Client with IP {client_ip} connected!")
            case ClientCommands.AVAILABLE_DRONES_REQUEST.value:
                console.log("Received request to get available drones from the client. Sending available drones...")
                drones_status = {}
                for drone_ip, drone in drones.items():
                    drones_status[drone_ip] = {"id": drone.id, "available": drone.available}
                client.send(f"{ClientCommands.AVAILABLE_DRONES_RESPONSE} {json.dumps(drones_status)}".encode())
            case ClientCommands.SHIPMENT_REQUEST.value:
                drone_ip = None
                drone_id = None
                if re.match("192\.168\.1\.(25[0-4]|2[0-4]\d|1\d\d|[1-9]\d|[2-9])$", arguments[0]) is None:
                    drone_id = arguments[0]
                    for ip, drone in drones.items():
                        if drone.id == drone_id:
                            drone_ip = ip
                else:
                    drone_ip = arguments[0]
                    drone_id = drones[drone_ip].id
                address = arguments[1]
                console.log(f"Client ({client_ip}) requested a delivery to {address} using drone {drone_ip}")
                if drone_ip in drones and drones[drone_ip].available:
                    drones_socket.sendto(f"{DroneCommands.DELIVERY_REQUEST} {drone_ip} {address}".encode(),
                                         drones[drone_ip].addr)
                    drones[drone_ip].available = False
                    console.log(f"Shipment request sent to {drone_ip}")
                else:
                    console.log(f"Drone {arguments[0]} is not available")
                    client.send(f"{ClientCommands.DRONE_NOT_AVAILABLE} {arguments[0]}".encode())
except KeyboardInterrupt:
    console.print()  # Print new line
    console.log("Closing connection")
    if client is not None:
        client.close()

    client_socket.close()
    drones_socket.close()
