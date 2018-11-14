import pytest
from beiran_package_docker.image_ref import normalize_ref

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

def test_normalize_ref(ref, normalized):
    assert normalize_ref(ref, marshal=True) == normalized

