from typing import Optional, Any
from hp3parclient import client, exceptions

from fosutil.config import secrets


class Hpe3Par:
    def __init__(self, name: str):
        self.name = name
        for ar in secrets["arrays"]:
            if ar["name"] == self.name:
                self.host = ar["host"]
                self.username = ar["username"]
                self.password = ar["password"]
        self.client: Optional[client.HP3ParClient] = None

    def connect(self) -> client.HP3ParClient:
        self.client = client.HP3ParClient(f"https://{self.host}:8080/api/v1")
        self.client.login(self.username, self.password)
        print(f"Connection established with array {self.name} ({self.host})")
        return self.client

    def disconnect(self) -> None:
        if self.client:
            self.client.logout()
            print(f"Connection with {self.name} ({self.host}) terminated")

    def get_defined_hosts(self) -> dict:
        available_host_sets = self.client.getHostSets()
        for m in available_host_sets["members"]:
            print(m["name"], m["setmembers"])
        return available_host_sets

    def remove_host_from_its_hostset(self, host_name: str) -> None:
        host_sets = self.client.getHostSets()
        for hs in host_sets["members"]:
            hosts_in_set = self.client.getHostSet(hs["name"])["members"]
            for h in hosts_in_set:
                if h["name"] == host_name:
                    self.client.modifyHostSet(hs["name"], 2, None, None, [host_name])
                    print(f"Removed {host_name} from hostset {hs['name']}")
                    break

    def delete_host(self, host_name: str) -> None:
        self.client.deleteHost(host_name)

    def create_host(
        self,
        host_name: str,
        persona: Optional[dict] = None,
        wwns: Optional[list] = None,
    ) -> None:
        self.client.createHost(host_name, None, wwns, persona)