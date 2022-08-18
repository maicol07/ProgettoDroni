import typing
from enum import Enum

from utils import get_command


class Commands(Enum):
    AVAILABLE_DRONES_REQUEST = "AVAILABLE-DRONES-REQUEST"
    SHIPMENT_REQUEST = "SHIPMENT-REQUEST"
    DRONE_DELIVERED = "DRONE-SHIPMENT-DELIVERED"
    DRONE_NOT_AVAILABLE = "DRONE-NOT-AVAILABLE"
    HELLO = "CLIENT-HELLO"
    AVAILABLE_DRONES_RESPONSE = "AVAILABLE-DRONES-RESPONSE"

    def __str__(self):
        return self.value


if __name__ == "__main__":
    import json
    import socket
    import threading
    from rich.console import Console
    from rich.prompt import Prompt

    from rich.table import Table

    available_drones: dict[str, dict[typing.Literal["id", "available"], typing.Union[str, bool]]] = {}
    available_drones_request_in_progress: bool = False

    def listen_messages():
        global available_drones_request_in_progress, available_drones, gateway_available

        while True:
            data = gateway.recv(15360).decode()
            if data == "":
                gateway.close()
                gateway_available = False
                break

            command, *arguments = get_command(data)
            match command:
                case Commands.AVAILABLE_DRONES_RESPONSE.value:
                    available_drones = json.loads(' '.join(arguments))
                    available_drones_request_in_progress = False
                case Commands.DRONE_DELIVERED.value:
                    console.log(f"Package delivered by drone {arguments[0]}", style="green")
                case Commands.DRONE_NOT_AVAILABLE.value:
                    console.log(f"Drone {arguments[0]} is not available", style="red")


    def send_available_drones_request():
        global available_drones_request_in_progress, gateway
        if not available_drones_request_in_progress and gateway_available:
            gateway.send(Commands.AVAILABLE_DRONES_REQUEST.value.encode())
            available_drones_request_in_progress = True
            t = threading.Thread(target=listen_messages, daemon=True)
            t.start()

    def wait_available_drones():
        with console.status("Requesting available drones..."):
            send_available_drones_request()
            while True:
                if not gateway_available or not available_drones_request_in_progress:
                    break

    def send_shipment(address: str, drone_ip: str):
        if gateway_available:
            console.log(f"Delivering to {address} by {drone_ip}...")
            gateway.send(f'{Commands.SHIPMENT_REQUEST} {drone_ip} {address}'.encode())
            t = threading.Thread(target=listen_messages, daemon=True)
            t.start()


    console = Console()

    gateway = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        gateway.connect(("localhost", 8810))
    except ConnectionRefusedError:
        console.print("Can't connect to the gateway. Check that it is running", style="red")
        exit(1)

    gateway_available = True
    gateway.send(f"{Commands.HELLO} 10.10.10.2".encode())
    console.log("Connected to the gateway")

    try:
        while True:
            if not gateway_available:
                console.print("Can't connect to the gateway. Check that it is running", style="red")
                exit(1)

            command = Prompt.ask("\nSelect a command:\n\ts. Send shipment\n\tg. Get available drones\n\te. Exit\n\n",
                                 choices=["s", "g", "e"])

            match command:
                case "s":
                    wait_available_drones()

                    drones = list(filter(
                        lambda drone: drone[1]["available"] is True,
                        available_drones.items()
                    ))
                    if len(drones) == 0:
                        console.log("No drones available", style="red")
                        continue

                    choices = []
                    for drone_ip, drone_data in drones:
                        choices.append(drone_data["id"])
                        choices.append(drone_ip)

                    drone_ip = Prompt.ask("Enter drone ID or IP address", choices=choices)
                    address = console.input("Enter the address to ship to: ")
                    t = threading.Thread(target=send_shipment, args=(address, drone_ip))
                    t.start()
                case "g":
                    wait_available_drones()

                    if len(available_drones) == 0:
                        console.log("No drones available", style="magenta")
                    else:
                        table = Table(title="Available drones")
                        table.add_column("ID", width=15)
                        table.add_column("IP", width=20)
                        table.add_column("Status", width=20)
                        for drone_ip, drone_data in available_drones.items():
                            table.add_row(
                                drone_data["id"],
                                drone_ip,
                                "🟢 Available" if drone_data["available"] else "🔴 Unavailable"
                            )

                        console.print(table)
                case "e":
                    break
    except KeyboardInterrupt:
        console.print()  # Print new line
    console.log("Closing connection")
    gateway.close()
