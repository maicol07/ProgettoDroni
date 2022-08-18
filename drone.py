from enum import Enum

from utils import get_command, unicode_input


class Commands(Enum):
    READY = "DRONE-READY"
    DELIVERED = "DRONE-DELIVERED"
    DELIVERY_REQUEST = "SHIPMENT-REQUEST"
    CONNECTION_CLOSED = "DRONE-CONNECTION-CLOSED"
    CONFIRMED = "DRONE-CONFIRMED"
    ALREADY_CONNECTED = "DRONE-ALREADY-CONNECTED"

    def __str__(self):
        return self.value


if __name__ == "__main__":
    import random
    import re
    import time

    from rich.console import Console

    import socket

    console = Console()

    def ask_ip():
        drone_ip = ""
        while re.match("192\.168\.1\.(25[0-4]|2[0-4]\d|1\d\d|[1-9]\d|[2-9])$", drone_ip) is None:
            drone_ip = unicode_input(
                    console,
                    "Enter drone IP address (must be in 192.168.1.X format, where X is a number between 2 and 254): "
                )
        return drone_ip

    gateway = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    gateway_addr = ("localhost", 8811)

    drone_id = unicode_input(console, "Enter drone ID: ")
    drone_ip = ask_ip()
    try:
        gateway.sendto(f"{Commands.READY} {drone_ip} {drone_id}".encode(), gateway_addr)
    except BrokenPipeError:
        console.print("Can't connect to the gateway. Check that it is running", style="red")
        exit(1)

    try:
        while True:
            data, address = gateway.recvfrom(1024)

            command, *arguments = get_command(data)
            match command:
                case Commands.CONFIRMED.value:
                    console.log(f"Connected to gateway and ready to deliver...", style="green")
                case Commands.ALREADY_CONNECTED.value:
                    console.log(f"Drone {drone_ip} is already connected. Please set another IP address.", style="red")
                    drone_ip = ask_ip()
                    gateway.sendto(f"{Commands.READY} {drone_ip} {drone_id}".encode(), gateway_addr)
                case Commands.DELIVERY_REQUEST.value:
                    delivery_address = arguments[1]
                    with console.status(f"Delivering to {delivery_address}..."):
                        time.sleep(random.randrange(2, 20))

                    console.log("Package delivered to", delivery_address, style="green")
                    gateway.sendto(f'{Commands.DELIVERED} {drone_ip}'.encode(), address)
    except KeyboardInterrupt:
        console.print()  # Print new line
        console.log("Closing...")
    gateway.sendto(f"{Commands.CONNECTION_CLOSED} {drone_ip}".encode(), gateway_addr)
    gateway.close()
