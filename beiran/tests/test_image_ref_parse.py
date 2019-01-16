# Beiran P2P Package Distribution Layer
# Copyright (C) 2019  Rainlab Inc & Creationline, Inc & Beiran Contributors
#
# Rainlab Inc. https://rainlab.co.jp
# Creationline, Inc. https://creationline.com">
# Beiran Contributors https://docs.beiran.io/contributors.html
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import pytest
from beiran_package_docker.image_ref import marshal_normalize_ref

@pytest.mark.parametrize('ref,normalized', [
    ('ubuntu', 'docker.io/library/ubuntu:latest'),
    ('ubuntu:14.04', 'docker.io/library/ubuntu:14.04'),
    ('repo/ubuntu', 'docker.io/repo/ubuntu:latest'),
    ('repo/ubuntu:14.04', 'docker.io/repo/ubuntu:14.04'),
    ('path/repo/ubuntu:14.04', 'docker.io/path/repo/ubuntu:14.04'),
    ('domain.com/ubuntu', 'domain.com/ubuntu:latest'),

    ('domain.com/repo/ubuntu', 'domain.com/repo/ubuntu:latest'),
    ('domain.com/repo/ubuntu:14.04', 'domain.com/repo/ubuntu:14.04'),
    ('domain.com/path/repo/ubuntu:14.04', 'domain.com/path/repo/ubuntu:14.04'),

    ('localhost:8080/repo/ubuntu', 'localhost:8080/repo/ubuntu:latest'),
    ('localhost:8080/repo/ubuntu:14.04', 'localhost:8080/repo/ubuntu:14.04'),
    ('localhost:8080/path/repo/ubuntu:14.04', 'localhost:8080/path/repo/ubuntu:14.04'),

    ('ubuntu@sha256:cb96ec8eb632c873d5130053cf5e2548234e5275d8115a39394289d96c9963a6',
     'docker.io/library/ubuntu@sha256:cb96ec8eb632c873d5130053cf5e2548234e5275d8115a39394289d96c9963a6'),
    ('repo/ubuntu@sha256:cb96ec8eb632c873d5130053cf5e2548234e5275d8115a39394289d96c9963a6',
     'docker.io/repo/ubuntu@sha256:cb96ec8eb632c873d5130053cf5e2548234e5275d8115a39394289d96c9963a6'),
    ('domain.com/repo/ubuntu@sha256:cb96ec8eb632c873d5130053cf5e2548234e5275d8115a39394289d96c9963a6', 
     'domain.com/repo/ubuntu@sha256:cb96ec8eb632c873d5130053cf5e2548234e5275d8115a39394289d96c9963a6'),
    ('localhost:8000/repo/ubuntu@sha256:cb96ec8eb632c873d5130053cf5e2548234e5275d8115a39394289d96c9963a6', 
     'localhost:8000/repo/ubuntu@sha256:cb96ec8eb632c873d5130053cf5e2548234e5275d8115a39394289d96c9963a6'),
    ('localhost:8000/path/repo/ubuntu@sha256:cb96ec8eb632c873d5130053cf5e2548234e5275d8115a39394289d96c9963a6', 
     'localhost:8000/path/repo/ubuntu@sha256:cb96ec8eb632c873d5130053cf5e2548234e5275d8115a39394289d96c9963a6'),
])

def test_marshal_normalize_ref(ref, normalized):
    assert marshal_normalize_ref(ref) == normalized

