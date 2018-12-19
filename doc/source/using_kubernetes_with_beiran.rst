============================
Using Kubernetes with Beiran
============================
When k8s plugin is in effect, Beiran has an endpoint of **CRI v1alpha2** so we can choose Beiran as a remote image service for k8s. By running beiran on each node of the k8s cluster, you can download layers contained in the image from other nodes in the cluster distributedly when an event to pull image occurs.

Configuration
-------------
That's very simple. Give the path of Belean's cri endpoint to kubelet's command option **"--image-service-endpoint"** and restart kubelet::

    kubelet --image-service-endpoint=path-to-grpc-socket

For example, if you are running kubelet with systemd, please edit the configuration file like as follows::

    [Service]

    ...

    Environment="KUBELET_CERTIFICATE_ARGS=--rotate-certificates=true --cert-dir=/var/lib/kubelet/pki"
    Environment="KUBELET_EXTRA_ARGS=--image-service-endpoint=unix:///var/run/beiran-cri.sock"
    ExecStart=
    ExecStart=/usr/bin/kubelet $KUBELET_KUBECONFIG_ARGS $KUBELET_SYSTEM_PODS_ARGS $KUBELET_NETWORK_ARGS $KUBELET_DNS_ARGS $KUBELET_AUTHZ_ARGS $KUBELET_CADVISOR_ARGS $KUBELET_CERTIFICATE_ARGS $KUBELET_EXTRA_ARGS
