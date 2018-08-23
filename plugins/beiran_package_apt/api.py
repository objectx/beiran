"""Docker API endpoints"""
from tornado import web
from tornado.web import HTTPError
from .models import AptPackage, PackageLocation
from .util import AptUtil as util


class Services:
    """These needs to be injected from the plugin init code"""
    local_node = None
    logger = None
    apt_cache_dir = "apt/cache"
    loop = None
    daemon = None
    distro = None
    release = None


class PackageDownload(web.RequestHandler):
    """
    ```bash

    $ curl --verbose http://mirror.de.leaseweb.net/debian/pool/main/n/nginx/nginx_1.10.3-1+deb9u1_all.deb --output nginx_1.10.3-1+deb9u1_all.deb
      % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                     Dload  Upload   Total   Spent    Left  Speed
      0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0*   Trying 37.58.58.140...
    * TCP_NODELAY set
    * Connected to mirror.de.leaseweb.net (37.58.58.140) port 80 (#0)
    > GET /debian/pool/main/n/nginx/nginx_1.10.3-1+deb9u1_all.deb HTTP/1.1
    > Host: mirror.de.leaseweb.net
    > User-Agent: curl/7.61.0
    > Accept: */*
    > 
    < HTTP/1.1 200 OK
    < Server: nginx/1.14.0
    < Date: Sat, 28 Jul 2018 15:20:21 GMT
    < Content-Type: application/octet-stream
    < Content-Length: 81502
    < Last-Modified: Wed, 12 Jul 2017 21:47:01 GMT
    < Connection: keep-alive
    < ETag: "596698d5-13e5e"
    < Accept-Ranges: bytes
    < 
    
    ```

    """

    def data_received(self, chunk):
        pass

    async def find_package(self, package_address):
        """
        Try to find package local or from remote.

        Args:
            package_address (str): package name

        Returns:
            tuple(AptPackage, str): AptPackage instance and

        """
        remote_uri = "http://{}".format(package_address)

        p_location, package = None, None

        try:
            p_location = PackageLocation.get(location=remote_uri)
            package = AptPackage.get(sha256=p_location.sha256)
        except (PackageLocation.DoesNotExist, AptPackage.DoesNotExist):
            pass

        if not p_location or not package:
            downloaded_package_path = await util.download_deb_file(remote_uri=remote_uri)
            if not downloaded_package_path:
                raise HTTPError("Can not download deb file!")

            package_path, package_data = await util.get_data_from_deb_file(downloaded_package_path)
            package = AptPackage.from_dict(package_data)
            package = AptPackage.add_or_update(package)
            package.store_binary(package_path)

        return package

    async def get(self, package_address):
        """
        Try to find package, read from local storage and stream it.

        Args:
            package_address (str): package uri

        Returns:
            HTTPResponse:

        """
        package = self.find_package(package_address)

    @staticmethod
    async def stream_deb(package):
        """

        Args:
            package (AptPackage): apt package

        Returns:
            stream from local storage

        """
        with open(package.storage_path, 'rb'):
            ...  # stream file with appropriate headers

    async def head(self, package_address):
        package = await self.find_package(package_address)


ROUTES = [
    (r'/apt/(.*\.deb)', PackageDownload),
    (r'/apt/(.*)', web.RedirectHandler, {"url": "http://{0}"}),
]
