"""Email backends used by Legajo."""

import socket
import smtplib
from django.core.mail.backends.smtp import DNS_NAME

from django.core.mail.backends.smtp import EmailBackend


class IPv4SocketMixin:
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


class IPv4SMTP(IPv4SocketMixin, smtplib.SMTP):
    pass


class IPv4SMTP_SSL(IPv4SocketMixin, smtplib.SMTP_SSL):
    pass


class IPv4SMTPEmailBackend(EmailBackend):
    def open(self):
        if self.connection:
            return False

        connection_params = {'local_hostname': DNS_NAME.get_fqdn()}
        if self.timeout is not None:
            connection_params['timeout'] = self.timeout
        if self.use_ssl:
            connection_params['context'] = self.ssl_context

        connection_class = IPv4SMTP_SSL if self.use_ssl else IPv4SMTP

        try:
            self.connection = connection_class(self.host, self.port, **connection_params)
            if not self.use_ssl and self.use_tls:
                self.connection.starttls(context=self.ssl_context)
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except OSError:
            if not self.fail_silently:
                raise
