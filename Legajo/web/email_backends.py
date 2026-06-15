"""Email backends used by Legajo."""

import socket
import smtplib

from django.core.mail.backends.smtp import EmailBackend


class IPv4SMTP(smtplib.SMTP):
    """SMTP client that avoids IPv6 routes unavailable in some hosts."""

    def _get_socket(self, host, port, timeout):
        if self.debuglevel > 0:
            self._print_debug('connect: to', (host, port), self.source_address)

        last_error = None
        for family, socktype, proto, _, address in socket.getaddrinfo(
            host,
            port,
            socket.AF_INET,
            socket.SOCK_STREAM,
        ):
            sock = None
            try:
                sock = socket.socket(family, socktype, proto)
                if timeout is not None:
                    sock.settimeout(timeout)
                if self.source_address:
                    sock.bind(self.source_address)
                sock.connect(address)
                return sock
            except OSError as exc:
                last_error = exc
                if sock is not None:
                    sock.close()

        if last_error is not None:
            raise last_error
        raise OSError(f'Could not resolve an IPv4 address for {host}')


class IPv4SMTPEmailBackend(EmailBackend):
    connection_class = IPv4SMTP
