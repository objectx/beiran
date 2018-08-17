from peewee import CharField, IntegerField, TextField
from beiran.models.base import BaseModel, JSONStringField

DEB_CACHE_DIR = "/var/lib/beiran/apt"


class AptPackage(BaseModel):
    """Apt Package Data Model

    A deb package has the followings metadata:

    Package: nginx
    Version: 1.10.3-1+deb9u1
    Installed-Size: 91
    Maintainer: Debian Nginx Maintainers <pkg-nginx-maintainers@lists.alioth.debian.org>
    Architecture: all
    Depends: nginx-full (<< 1.10.3-1+deb9u1.1~) | nginx-light (<< 1.10.3-1+deb9u1.1~) | nginx-extras (<< 1.10.3-1+deb9u1.1~), nginx-full (>= 1.10.3-1+deb9u1) | nginx-light (>= 1.10.3-1+deb9u1) | nginx-extras (>= 1.10.3-1+deb9u1)
    Description: small, powerful, scalable web/proxy server
    Description-md5: 04f6acc7fe672a4d62f4345c9addf4a7
    Homepage: http://nginx.net
    Tag: implemented-in::c, interface::daemon, network::server, network::service,
     protocol::http, role::program, use::proxying
    Section: httpd
    Priority: optional
    Filename: pool/main/n/nginx/nginx_1.10.3-1+deb9u1_all.deb
    Size: 81502
    MD5sum: c95b559748017d27c5d23f42261a4a4b
    SHA256: 951dfb23d22013100af05b9237be5cf35e3eef987c75ca112bc130fa91e65679

    """

    package = CharField(max_length=64)      # docker-ce
    version = CharField(max_length=32)      # 17.03.0~ce-0~debian-jessie
    filename = CharField(max_length=512)    # dists/jessie/pool/stable/amd64/docker-ce_17.03.0~ce-0~debian-jessie_amd64.deb
    size = IntegerField()                   # 19009944
    md5sum = CharField(max_length=32)       # 16deb7601fe7a984718e6e144dc83e82
    sha256 = CharField(max_length=64, primary_key=True)  # 62714e9eae6b0b650e1c4571494f6b90a10ba62c8244f10e410a8d855034d324

    # beiran info
    available_at = JSONStringField(default=list)
    local_path = TextField(null=True)

    @classmethod
    def add_or_update(cls, pkg):
        """
        Update with or create a new node object from provided `node` object.
        Args:
            node (Node): node object

        Returns:
            (Node): node object


        TODO: move this method to BaseModel

        We can add an attribute for primary key ('uuid for default') and a property method can
        return the attribute which is defined different per each model if necessary.

            class Base:
                PRIMARY_KEY = 'uuid'

                @property
                def primary_key(self):
                    return self.__getattribute__(self.primary_key)

            class AptPackage:
                PRIMARY_KEY = 'sha256'


        or Peewee already provides a method called `get_primary_keys`, look that up!

        """
        try:
            pkg_ = cls.get(cls.sha256 == pkg.sha256)
            pkg_.update_using_obj(pkg)
            pkg_.save()

        except cls.DoesNotExist:
            pkg_ = pkg
            # https://github.com/coleifer/peewee/blob/0ed129baf1d6a0855afa1fa27cde5614eb9b2e57/peewee.py#L5103
            pkg_.save(force_insert=True)

        return pkg_

    # @property
    # def storage_path(self):
    #     return self.local_path or "{}/{}/{}/{}".format(
    #         DEB_CACHE_DIR,
    #         self.repository,
    #         self.filename,
    #     )
    #


class PackageLocation(BaseModel):
    """
    This model represents a map from package hash to available remote location of a package.

    Examples:
        62714e9eae6..., http://de.debian.org/debian/dists/jessie/pool/stable/amd64/docker-ce_17.03.0~ce-0~debian-jessie_amd64.deb
        62714e9eae6..., http://jp.debian.org/debian/dists/lenny/pool/stable/amd64/docker-ce_17.03.0~ce-0~debian-jessie_amd64.deb

        Same package can be found in different locations.

    """

    sha256 = CharField(max_length=64)
    location = CharField(max_length=512)

    class Meta:
        indexes = (
            # create a unique together on sha256 / location
            (('sha256', 'location', ), True),
        )

MODEL_LIST = [
    AptPackage,
    PackageLocation,
]
