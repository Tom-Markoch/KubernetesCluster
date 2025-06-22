![t](https://www.indiemapspot.com/telemetry/t.png)
  Copyright (C) 2024 Tomislav Markoc, unpublished work. All rights reserved.
  Title and version: KubernetesCluster, version 2.0

  This is an unpublished work registered with the U.S. Copyright Office. As
  per https://www.copyright.gov/comp3/chap1900/ch1900-publication.pdf and
  https://www.govinfo.gov/content/pkg/USCODE-2011-title17/pdf/USCODE-2011-title17-chap1-sec101.pdf,
  public performance or a public display of a work "does not of itself
  constitute publication." Therefore, you only have permission to view this
  work in your web browser.

  You do not do not have permission to make copies by downloading files,
  copy and paste texts, use git clone, clone, fork, or use any other means
  to make copies of this work.

  If you make a copy of this work, you must delete it immediately.

  You do not have permission to modify this work or create derivative work.

  You do not have permission to use this work for any Artificial Intelligence
  (AI) purposes, including and not limited to training AI models or
  generative AI.

  By hosting this work you accept this agreement.

  In the case of conflict this licensing agreement takes precedence over all
  other agreements.

  In the case any provision of this licensing agreement is invalid or
  unenforceable, any invalidity or unenforceability will affect only that
  provision.

  ---------------------------------------------------------------------------

  Copyright statutory damages are up to $150,000 for willful infringement.
  Other damages may be more.

  This work was created without AI assistance. Therefore, the copyright
  status is clear.

  For info about this work or demo, contact me at tmarkoc@hotmail.com.

# Introduction
This project consists of a set of python and bash scripts that can be used to easily and quickly create native Kubernetes cluster. This is a fully functional, pure Kubernetes system capable of creating HA Cluster on a cloud, bare metal cluster or cluster using Hyper-V VM-s on a Windows Pro laptop. This project does not try to replace kubeadm and kubectl, it just makes it much easier to create native Kubernetes cluster so kubeadm and kubectl can be used to operate the cluster. This project does not use MiniKube, MicroK8s or similar technologies.

Cluster is created by using Ubuntu Servers (or Ubuntu Desktops for development purposes), and by using containerd and Cilium. Memory to disk swapping is turned on (new Kubernetes feature).

Approach taken is to first create OS image with Kubernetes preinstalled and container images preloaded. Then, from this image it is possible to create new Kubernetes nodes and join them to the cluster in a matter of a few dozen seconds. This way it is even possible to recreate entire cluster very quickly.

# Supported Configurations
## Azure Cluster (HA Production Cluster or Dev/Test Cluster)
Any number of Scale Sets and VM-s, up to the Azure limit. Scale sets can be either with Reserved or with Spot pricing.

For HA production cluster, load balancer is used.
For Dev/Test cluster, load balancer is replaced with a reserved instance VM.

```mermaid
architecture-beta
    group cloud(cloud)[Cloud]

    group scaleset0(server)[Scale Set 0] in cloud
    service nodess0n0(server)[Node 0] in scaleset0
    service nodess0n1(server)[Node 1] in scaleset0
    service nodess0n2(server)[Node 2] in scaleset0
    service nodess0n3(server)[Node 3] in scaleset0
    junction jss0n0 in scaleset0
    junction jss0n1 in scaleset0
    junction jss0n2 in scaleset0
    junction jss0n3 in scaleset0
    junction jss0n4 in scaleset0
    nodess0n0:T -- B:jss0n0
    nodess0n1:T -- B:jss0n1
    nodess0n2:T -- B:jss0n2
    nodess0n3:T -- B:jss0n3
    jss0n0:R -- L:jss0n1
    jss0n1:R -- L:jss0n2
    jss0n2:R -- L:jss0n3
    jss0n3:R --> L:jss0n4

    group scaleset1(server)[Scale Set 1] in cloud
    service nodess1n0(server)[Node 0] in scaleset1
    service nodess1n1(server)[Node 1] in scaleset1
    service nodess1n2(server)[Node 2] in scaleset1
    service nodess1n3(server)[Node 3] in scaleset1
    junction jss1n0 in scaleset1
    junction jss1n1 in scaleset1
    junction jss1n2 in scaleset1
    junction jss1n3 in scaleset1
    junction jss1n4 in scaleset1
    nodess1n0:T -- B:jss1n0
    nodess1n1:T -- B:jss1n1
    nodess1n2:T -- B:jss1n2
    nodess1n3:T -- B:jss1n3
    jss1n0:R -- L:jss1n1
    jss1n1:R -- L:jss1n2
    jss1n2:R -- L:jss1n3
    jss1n3:R --> L:jss1n4

    junction jss0 in cloud
    junction jss1 in cloud
    junction jss2 in cloud
    junction jss3 in cloud

    jss0:R -- L:jss0n0
    jss2:R -- L:jss1n0

    jss0:B -- T:jss1
    jss1:B -- T:jss2
    jss2:B --> T:jss3

    service loadbalancer(server)[Load Balancer OR Main Node VM] in cloud
    loadbalancer:R -- L:jss0

    service nsg(server)[Network Security Group] in cloud
    nsg:R -- L:jss1

    service publicip(cloud)[Public IP] in cloud
    publicip:R -- L:loadbalancer
    
    service internet(internet)[Internet]
    internet:R --> L:publicip
```

## HA Bare Metal Cluster
```mermaid
architecture-beta
    group cluster(server)[HA Bare Metal Cluster or Windows Pro HyperV Development Cluster]
    service node0(server)[Node 0] in cluster
    service node1(server)[Node 1] in cluster
    service node2(server)[Node 2] in cluster
    service node3(server)[Node 3] in cluster
    junction j0 in cluster
    junction j1 in cluster
    junction j2 in cluster
    junction j3 in cluster
    junction j4 in cluster
    node0:T -- B:j0
    node1:T -- B:j1
    node2:T -- B:j2
    node3:T -- B:j3
    j0:R -- L:j1
    j1:R -- L:j2
    j2:R -- L:j3
    j3:R --> L:j4

    service lb(server)[External Load Balancer]
    service internet(internet)[Internet]
    lb:R -- L:j0
    internet:R -- L:lb
```

## Dev Cluster made of Hyper-V VMs on Windows Pro
```mermaid
architecture-beta
    group cluster(server)[Windows Pro HyperV Development Cluster]
    service nodem(server)[Main Node] in cluster
    service node0(server)[Node 0] in cluster
    service node1(server)[Node 1] in cluster
    service node2(server)[Node 2] in cluster
    service node3(server)[Node 3] in cluster
    junction jm in cluster
    junction j0 in cluster
    junction j1 in cluster
    junction j2 in cluster
    junction j3 in cluster
    junction j4 in cluster
    nodem:T -- B:jm
    node0:T -- B:j0
    node1:T -- B:j1
    node2:T -- B:j2
    node3:T -- B:j3
    jm:R -- L:j0
    j0:R -- L:j1
    j1:R -- L:j2
    j2:R -- L:j3
    j3:R --> L:j4

    service internet(internet)[Internet]
    internet:R -- L:nodem
```


# Cluster Creation
Recommended way to use the installation scripts is to create an Linux operating system image with preinstalled Kubernetes, and then quickly clone VM-s from that image. Once cloned VM is running, initialization script is used to provide all the necessary parameters and quickly execute "kubeadm init" or "kubeadm join". Alternatively, scripts can be used to install Kubernetes individualy on each machine, and then initialize and join the cluster.

## install_kube.sh - Script for Kubernetes Installation on Linux

```mermaid
flowchart TD
start((Start)) --> init_firewall["Initialize UFW Firewall"]
init_firewall --> init_etc_host["Set Kubernetes Control Plane Endpoint in /etc/hosts<br>Set IPv4 Forwarding"]
init_etc_host --> set_linux_config{{"Check cgroup v2<br>Check systemd"}}
set_linux_config --> | Checks failed | stop1((Stop))
set_linux_config --> | Checks passed| install_containerd["Install containerd"]
install_containerd --> install_kubernetes["Install Kubernetes"]
install_kubernetes --> install_cilium["Install Cilium"]
install_cilium --> load_services["(Pre)Load Kubernetes Ingress and Services<br>(Fully configurable step)"]
load_services --> test_pods["Verify pods running<br>(Fully configurable test)"]
test_pods --> test_endpoints["Test Ingress and/or Services endpoints<br>(Fully configurable test)"]
test_endpoints --> reset["kubeadm reset<br>"]
reset --> delete_firewall_rules["Delete unnecessary rules from the UFW firewall"]
delete_firewall_rules --> azure{{"Creating Azure VM Image?"}}
azure --> |yes| generalize[Generalize Linux OS]
generalize --> stop2((Stop))
azure --> |no| stop2
```

## initialize_kube_node.sh - Linux script for Kubernetes Cluster Initialization and Node Joining

```mermaid
flowchart TD
start((Start)) --> init_firewall["Setup UFW Firewall"]
init_firewall --> swap_mem["Turn on swap memory (Latest Kubernetes Feature)."]
swap_mem --> init_etc_host["Set Kubernetes Control Plane Endpoint in /etc/hosts"]
init_etc_host --> init_or_join{{"Init or Join?"}}
init_or_join --> | Init | init("kubeadm init")
init_or_join --> | Join | join("kubeadm join")
init --> control_plane
join --> control_plane
control_plane{{"Control Plane?"}}
control_plane --> | Yes | set_kubectl
set_kubectl("Setup kubectl")
set_kubectl --> allow_workloads{{"Allow workloads?"}}
allow_workloads --> | Yes | enable_workloads("Enable workloads")
enable_workloads --> is_init{{"Is init?"}}
allow_workloads --> | No | is_init
control_plane --> | No | stop((Stop))
is_init --> | Yes | cilium("Load Cilium networking")
cilium --> stop
is_init --> | No | stop
```

## Azure Cluster Creation

```mermaid
flowchart TD
start((Start)) --> vm_image_storage["Manually create azure resource group for storing VM images."]
vm_image_storage --> kube_settings["Edit kube_settings.json"]
kube_settings --> create_azure_vm_image.py

subgraph create_azure_vm_image.py
  azure_image_script_start["Verify image does not already exist"]
  azure_image_script_start --> create_rg["Create temporary image creation rg, ip, nsg, vnet, vm"]
  create_rg --> ssh["Install SSH key"]
  ssh --> linux_install["Run install_kube.sh"]
  linux_install --> save_image["Deallocate VM<br>Azure generalize VM<br>Save VM image"<br>Delete temporary image creation rg and resources]
end

create_azure_vm_image.py --> vm_image[(Linux VM image with preinstalled Kubernetes, containerd, Cilium and preloaded pod images is created!)]
vm_image --> azure_cluster.py

subgraph azure_cluster.py
  cluster_already_created{{"Cluster already created?"}}
  cluster_already_created --> | No | create_cluster
  create_cluster["Create cluster rg, ip, nsg, vnet, load balancer"]
  create_cluster --> create_scale_sets["From VM Image clone scale set VMs"]
  cluster_already_created --> | Yes | ui
  create_scale_sets --> ui["Run UI to init, join, reset nodes or apply configurations"]
  ui --> resize["Resize scale sets and refresh UI"] --> ui
  ui --> quit((Quit script))
end
azure_cluster.py --> stop((Stop))
```

## Bare Metal or Windows Pro Hyper-V VM Cluster Creation

You can either use script to install Kubernetes on each machine separately, or install on one machine and then manually create .ISO image or VM image and then clone many machines from that image. After machines are installed or cloned, use script again to init, join, reset nodes or apply cluster configurations.

```mermaid
flowchart TD
start((Start)) --> start_machines["Edit kube_settings.json and list all machines IPs"]
start_machines --> metal_cluster.py

subgraph metal_cluster.py
  ui["Run UI to install, init, join, reset nodes or apply configurations"]
end

metal_cluster.py --> stop((Stop))
```
