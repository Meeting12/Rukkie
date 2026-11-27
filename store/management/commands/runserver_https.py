import ssl

from django.conf import settings
from django.contrib.staticfiles.handlers import StaticFilesHandler
from django.core.management.base import BaseCommand, CommandError
from django.core.servers.basehttp import ThreadedWSGIServer, WSGIRequestHandler, get_internal_wsgi_application


class LocalHTTPSWSGIServer(ThreadedWSGIServer):
    def setup_environ(self):
        super().setup_environ()
        # Django gets its scheme from WSGI after this server terminates TLS.
        self.base_environ['HTTPS'] = 'on'


class Command(BaseCommand):
    help = 'Run the development server over HTTPS on 127.0.0.1.'

    def add_arguments(self, parser):
        parser.add_argument('--certfile', required=True, help='Local PEM certificate')
        parser.add_argument('--keyfile', required=True, help='Local PEM private key')
        parser.add_argument('--port', type=int, default=8443)

    def handle(self, **options):
        if not settings.DEBUG:
            raise CommandError('The local HTTPS server requires DEBUG=True.')
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        try:
            tls.load_cert_chain(options['certfile'], options['keyfile'])
        except (OSError, ValueError) as error:
            raise CommandError(f'Could not load the local certificate and key: {error}') from error

        address = ('127.0.0.1', options['port'])
        application = StaticFilesHandler(get_internal_wsgi_application())
        try:
            with LocalHTTPSWSGIServer(address, WSGIRequestHandler, allow_reuse_address=False) as server:
                server.socket = tls.wrap_socket(server.socket, server_side=True)
                server.set_app(application)
                self.stdout.write(f'Local HTTPS server at https://127.0.0.1:{server.server_port}/')
                server.serve_forever()
        except KeyboardInterrupt:
            return
        except OSError as error:
            raise CommandError(f'Could not start the local HTTPS server: {error}') from error
