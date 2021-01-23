import requests
import logging

from .exceptions import ConnectionException, AuthenticationException


class SaltClient(object):
    def __init__(self, salt_host, salt_username, salt_password, **kwargs):
        self.token = None
        self.salt_host = salt_host
        self.salt_username = salt_username
        self.salt_password = salt_password
        self.verify_ssl_cert = kwargs.get("verify_ssl_cert", False)

    def login(self):
        req = requests.post(self.salt_host + "/login", data={"eauth": "pam", "username": self.salt_username, "password": self.salt_password}, headers={"Accept": "application/json"}, verify=self.verify_ssl_cert, timeout=5.0)
        if req.status_code != 200:
            raise ConnectionException("Signing in to salt (%s) failed with status code %s (body %s)" % (self.salt_host, req.status_code, req.text))
        logging.debug("Salt login response: %s - %s", req.status_code, req.text)
        if req.status_code != 200:
            raise AuthenticationException("Signing in to salt failed.")
        resp = req.json()
        self.token = resp["return"][0]["token"]
        return self.token

    def _get_headers(self):
        return {"Accept": "application/json", "X-Auth-Token": self.token}

    def is_minion_reachable(self, minion_id):
        req = requests.post(self.salt_host, data={"client": "local", "tgt": minion_id, "fun": "test.ping"}, headers=self._get_headers(), verify=self.verify_ssl_cert)
        logging.debug("Salt ping response: %s - %s", req.status_code, req.text)
        resp = req.json()
        data = resp["return"][0]
        if len(data) == 0:  # returns [{}] if request fails
            return False
        if data.get(minion_id):  # returns [{"node-name": True}] if ping succeeds
            return True
        return None

    def run_async_command(self, target, command, args):
        resp = requests.post(self.salt_host, data={"client": "local_async", "tgt": target, "fun": command, "arg": args}, headers=self._get_headers(), verify=self.verify_ssl_cert)
        logging.debug("Salt cmd response: %s - %s", resp.status_code, resp.text)
        data = resp.json()
        return data["return"][0]["jid"]

    def check_job_status(self, job_id):
        resp = requests.post(self.salt_host, data={"client": "runner", "fun": "jobs.lookup_jid", "jid": job_id}, headers=self._get_headers(), verify=self.verify_ssl_cert)
        logging.debug("lookup_jid response: %s - %s", resp.status_code, resp.text)
        data = resp.json()
        return data

    def run_command(self, target, command, args):
        resp = requests.post(self.salt_host, data={"client": "local", "tgt": target, "fun": command, "arg": args}, headers=self._get_headers(), verify=self.verify_ssl_cert)
        logging.debug("Salt cmd response: %s - %s", resp.status_code, resp.text)
        data = resp.json()

        machines = data["return"][0]
        for machine, machine_data in machines.items():
            for _, command_data in machine_data.items():
                if not command_data["result"]:
                    return False
        return True
