#!/bin/bash
# Copyright (C) 2024 Tomislav Markoc, unpublished work. All rights reserved.
# Title and version: KubernetesCluster, version 2.0
#
# This is an unpublished work registered with the U.S. Copyright Office. As
# per https://www.copyright.gov/comp3/chap1900/ch1900-publication.pdf and
# https://www.govinfo.gov/content/pkg/USCODE-2011-title17/pdf/USCODE-2011-title17-chap1-sec101.pdf,
# public performance or a public display of a work "does not of itself
# constitute publication." Therefore, you only have permission to view this
# work in your web browser.
#
# You do not do not have permission to make copies by downloading files,
# copy and paste texts, use git clone, clone, fork, or use any other means
# to make copies of this work.
#
# If you make a copy of this work, you must delete it immediately.
#
# You do not have permission to modify this work or create derivative work.
#
# You do not have permission to use this work for any Artificial Intelligence
# (AI) purposes, including and not limited to training AI models or
# generative AI.
#
# By hosting this work you accept this agreement.
#
# In the case of conflict this licensing agreement takes precedence over all
# other agreements.
#
# In the case any provision of this licensing agreement is invalid or
# unenforceable, any invalidity or unenforceability will affect only that
# provision.
#
# ---------------------------------------------------------------------------
#
# Copyright statutory damages are up to $150,000 for willful infringement.
# Other damages may be more.
#
# This work was created without AI assistance. Therefore, the copyright
# status is clear.
#
# For info about this work or demo, contact me at tmarkoc@hotmail.com.

# Usage:
# scp install_kube.sh '<username>@<ip-address>:$HOME/Documents/install_kube.sh'
# ssh -t <username>@<ip-address> 'bash $HOME/Documents/install_kube.sh <password> <azure_generalize> <cluster_address_prefix>'
# Example:
# ssh -t <username>@<ip-address> 'bash $HOME/Documents/install_kube.sh <password> generalize 1.2.3.4'

echo "###############################################################################"
echo "Running Kubernetes Installation Script..."
echo "###############################################################################"

echo $1 | sudo -S echo "LOADING PASSWORD"

set -e # End script on first error.
#set -x

azure_generalize=$2
cluster_address_prefix=$3
echo "azure_generalize=$azure_generalize"
echo "cluster_address_prefix=$cluster_address_prefix"

kube_control_plane_endpoint="127.0.0.1"

###############################################################################
###############################################################################

# There is equivalent UFW code in the initialization script.
# At the end of the script we remove all of the rules except ssh.
sudo ufw reset
sudo ufw allow ssh
# Allows default Kube service ip range (10.96.0.0/12) and our pod ip range set by podSubnet.
sudo ufw allow from 10.0.0.0/8
# Allows node ip range (and some Kube system services are in the same range).
sudo ufw allow from $cluster_address_prefix
# Allows load balancer ip address.
sudo ufw allow from $kube_control_plane_endpoint
# Allows Azure load balancer health probe.
# sudo ufw allow from 168.63.129.16 No need for load balancer probe here.
sudo ufw enable

mkdir -p $HOME/Downloads
mkdir -p $HOME/Documents

###############################################################################
###############################################################################

if grep -q control-plane-endpoint /etc/hosts; then
    echo "WARNING! /etc/hosts already contains control-plane-endpoint, overwritting!"
    sudo sed -i "s/.* control-plane-endpoint/$kube_control_plane_endpoint control-plane-endpoint/g" /etc/hosts
else
    echo "$kube_control_plane_endpoint control-plane-endpoint" | sudo tee -a /etc/hosts
fi

###############################################################################
###############################################################################

echo "Enable IPv4 forwarding..."
ipv4_forwarding=$(sysctl net.ipv4.ip_forward | awk '{ print $3 }')
if [[ $ipv4_forwarding -ne 1 ]]; then
# https://kubernetes.io/docs/setup/production-environment/container-runtimes/
# START OF COPYRIGHT UNCLAIMABLE MATERIAL. Public domain or Kubernetes organization.
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.ipv4.ip_forward = 1
EOF
# Apply without reboot.
sudo sysctl --system
# END OF COPYRIGHT UNCLAIMABLE MATERIAL.
fi

ipv4_forwarding=$(sysctl net.ipv4.ip_forward | awk '{ print $3 }')
if [[ $ipv4_forwarding -ne 1 ]]; then
    echo "ERROR, FAILED TO ENABLE IPv4 FORWARDING!"
    exit 1
else
    echo "IPv4 forwarding enabled."
fi

###############################################################################
###############################################################################

echo "Checking if OS uses group v2..."
# https://kubernetes.io/docs/concepts/architecture/cgroups/
cgroup=$(stat -fc %T /sys/fs/cgroup/)
if [[ $cgroup != "cgroup2fs" ]]; then
    echo "ERROR, THIS OS DOES NOT USE cgroup v2!"
    exit 1
else
    echo "cgroup v2 detected."
fi

###############################################################################
###############################################################################

echo "Checking if OS uses systemd..."
ps1_systemd=$(ps 1 | awk 'FNR == 2 {print $5}')
if [[ $ps1_systemd == "/sbin/init" ]]; then
    stat_systemd=$(stat /sbin/init | awk 'FNR == 1 {print $4}')
    if [[ $stat_systemd == "../lib/systemd/systemd" ]]; then
        echo "systemd detected."
    else
        echo "ERROR, THIS OS DOES NOT USE systemd!"
        exit 1
    fi
elif [[ $ps1_systemd == "/usr/lib/systemd/systemd" ]]; then
    echo "systemd detected."
else
    echo "ERROR, THIS OS DOES NOT USE systemd!"
    exit 1
fi

###############################################################################
###############################################################################

# START OF SECTION CONTAINING DE MINIMIS MATERIAL. Only lines marked "DE MINIMIS" are De Minimis 
# and are from Kubernetes organization or containerd organization installation instructions.

# Instructions from https://github.com/containerd/containerd/blob/main/docs/getting-started.md
echo "Installing containerd..."
containerd_filename="containerd-1.7.20-linux-amd64.tar.gz"
containerd_filename_sha256sum="${containerd_filename}.sha256sum"
wget -O "$HOME/Downloads/$containerd_filename" "https://github.com/containerd/containerd/releases/download/v1.7.20/$containerd_filename"
wget -O "$HOME/Downloads/$containerd_filename_sha256sum" "https://github.com/containerd/containerd/releases/download/v1.7.20/$containerd_filename_sha256sum"
current_dir=$(pwd)
cd $HOME/Downloads
sha256sum -c $containerd_filename_sha256sum
sudo tar Cxzvf /usr/local $containerd_filename # DE MINIMIS
cd $current_dir

sudo mkdir -p /usr/local/lib/systemd/system
sudo wget -O /usr/local/lib/systemd/system/containerd.service "https://raw.githubusercontent.com/containerd/containerd/main/containerd.service"
sudo systemctl daemon-reload # DE MINIMIS
sudo systemctl enable --now containerd # DE MINIMIS

wget -O "$HOME/Downloads/runc.amd64" "https://github.com/opencontainers/runc/releases/download/v1.1.13/runc.amd64"
wget -O "$HOME/Downloads/runc.amd64.asc" "https://github.com/opencontainers/runc/releases/download/v1.1.13/runc.amd64.asc"
# TODO: VERIFY ASC FILE!
sudo install -m 755 "$HOME/Downloads/runc.amd64" /usr/local/sbin/runc # DE MINIMIS

cni_filename="cni-plugins-linux-amd64-v1.5.1.tgz"
cni_filename_sha256="${cni_filename}.sha256"
wget -O "$HOME/Downloads/$cni_filename" "https://github.com/containernetworking/plugins/releases/download/v1.5.1/$cni_filename"
wget -O "$HOME/Downloads/$cni_filename_sha256" "https://github.com/containernetworking/plugins/releases/download/v1.5.1/$cni_filename_sha256"
current_dir=$(pwd)
cd $HOME/Downloads
sha256sum -c $cni_filename_sha256
cd $current_dir
sudo mkdir -p /opt/cni/bin # DE MINIMIS
sudo tar Cxzvf /opt/cni/bin "$HOME/Downloads/$cni_filename" # DE MINIMIS

# Instructions from https://kubernetes.io/docs/setup/production-environment/container-runtimes/
sudo mkdir -p /etc/containerd
sudo /usr/local/bin/containerd config default | sudo tee /etc/containerd/config.toml # DE MINIMIS

# END OF SECTION CONTAINING DE MINIMIS MATERIAL.

disabled_plugins_count=$(grep -o -i "disabled_plugins" /etc/containerd/config.toml | wc -l)
disabled_plugins_list_count=$(grep -o -i "disabled_plugins = \[\]" /etc/containerd/config.toml | wc -l)
if [ $disabled_plugins_count -ne 1 ] || [ $disabled_plugins_list_count -ne 1 ]; then
    echo "ERROR, unexpected disabled_plugins setting in default /etc/containerd/config.toml"
    exit 1
fi

# Set SystemdCgroup in /etc/containerd/config.toml .
systemd_count=$(grep -o -i "SystemdCgroup" /etc/containerd/config.toml | wc -l)
systemd_count_false=$(grep -o -i "SystemdCgroup = false" /etc/containerd/config.toml | wc -l)
if [ $systemd_count -ne 1 ] || [ $systemd_count_false -ne 1 ]; then
    echo "ERROR, unexpected SystemdCgroup setting in default /etc/containerd/config.toml"
    exit 1
else
    sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/g' /etc/containerd/config.toml
fi

systemd_count=$(grep -o -i "SystemdCgroup" /etc/containerd/config.toml | wc -l)
systemd_count_true=$(grep -o -i "SystemdCgroup = true" /etc/containerd/config.toml | wc -l)
if [ $systemd_count -ne 1 ] || [ $systemd_count_true -ne 1 ]; then
    echo "ERROR, could not set SystemdCgroup in /etc/containerd/config.toml"
    exit 1
fi

sudo systemctl restart containerd
sudo systemctl enable containerd

echo "Finished Installing containerd."

###############################################################################
###############################################################################

echo "Installing Kubernetes..."

# https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/install-kubeadm/
# START OF COPYRIGHT UNCLAIMABLE MATERIAL. Public domain or Kubernetes organization.
sudo apt-get update
sudo apt-get install -y apt-transport-https ca-certificates curl gpg
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list

sudo apt-get update
# sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-get install -y kubelet kubeadm kubectl --allow-change-held-packages
sudo apt-mark hold kubelet kubeadm kubectl
# END OF COPYRIGHT UNCLAIMABLE MATERIAL.

certificate_key=$(kubeadm certs certificate-key)
echo "$certificate_key" > "$HOME/Documents/certificate-key.txt"
###############################################################################
# IMPORTANT !!!
# "sudo swapoff -a" will not turn off swap permanently beacause it resets
# on restart. Instead, to permanently turn swap off, swap line in /etc/fstab
# must be comment out.
# OR enable Kubernetes swap, which is done next:
###############################################################################
cat <<EOF > "$HOME/Documents/kubeadm-config.yaml"
---
apiVersion: "kubeadm.k8s.io/v1beta3"
kind: InitConfiguration
certificateKey: "$certificate_key"
---
apiVersion: kubeadm.k8s.io/v1beta3
kind: ClusterConfiguration
controlPlaneEndpoint: control-plane-endpoint:6443
networking:
  podSubnet: "10.1.1.0/24" # instead of command line option --pod-network-cidr
featureGates:
  EtcdLearnerMode: false # disabled because it was causing problems when joining the node, error: "can only promote a learner member which is in sync with leader"
---
apiVersion: kubelet.config.k8s.io/v1beta1
kind: KubeletConfiguration
failSwapOn: false
featureGates:
  NodeSwap: true
memorySwap:
  swapBehavior: LimitedSwap
EOF

# NOTE: --pod-network-cidr moved to $HOME/Documents/kubeadm-config.yaml
# sudo kubeadm init --pod-network-cidr=10.1.1.0/24 --config "$HOME/Documents/kubeadm-config.yaml"
sudo kubeadm init --config "$HOME/Documents/kubeadm-config.yaml" --upload-certs --ignore-preflight-errors=NumCPU --ignore-preflight-errors=Mem

# https://kubernetes.io/docs/setup/production-environment/tools/kubeadm/create-cluster-kubeadm/
# START OF COPYRIGHT UNCLAIMABLE MATERIAL. Public domain.
mkdir -p $HOME/.kube
sudo cp /etc/kubernetes/admin.conf $HOME/.kube/config # "cp -i ..." to ask confirmation
sudo chown $(id -u):$(id -g) $HOME/.kube/config
# END OF COPYRIGHT UNCLAIMABLE MATERIAL.

kubectl taint nodes $(hostname) node-role.kubernetes.io/control-plane:NoSchedule-

echo "Finished Installing Kubernetes."

###############################################################################
###############################################################################

echo "Installing Cilium..."

# https://docs.cilium.io/en/stable/gettingstarted/k8s-install-default/
# START OF COPYRIGHT UNCLAIMABLE MATERIAL. Public domain or Cilium.
CILIUM_CLI_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/cilium-cli/main/stable.txt)
CLI_ARCH=amd64
if [ "$(uname -m)" = "aarch64" ]; then CLI_ARCH=arm64; fi
curl -L --fail --remote-name-all https://github.com/cilium/cilium-cli/releases/download/${CILIUM_CLI_VERSION}/cilium-linux-${CLI_ARCH}.tar.gz{,.sha256sum}
sha256sum --check cilium-linux-${CLI_ARCH}.tar.gz.sha256sum
sudo tar xzvfC cilium-linux-${CLI_ARCH}.tar.gz /usr/local/bin
rm cilium-linux-${CLI_ARCH}.tar.gz{,.sha256sum}

#TODO: DO NOT USE HARDCODED VERSION!
cilium install --version 1.15.7
# END OF COPYRIGHT UNCLAIMABLE MATERIAL.

###############################################################################
# BUG FIX:
# Cilium will not start properly because /opt/cni/bin ownership is not set
# to root:root. Error can be tracked down by running (replace cilium-XXXXX
# with proper pod name):
# kubectl describe pod cilium-XXXXX -n kube-system
# Following line fixes the issue:
sudo chown root:root /opt/cni/bin/
###############################################################################

echo "Finished Installing Cilium."

###############################################################################
###############################################################################

echo "Loading services and running tests..."

dest_config_dir="configurations/InstallKubernetes"
test_pod_names_path="$HOME/TestPodNames.txt"
test_endpoints_path="$HOME/TestEndpoints.txt"

# Create NodePort service with explicit node port number:
# Method 1:
# kubectl expose deployment $kubeapp_deployment_name --type=NodePort --name=$kubeapp_service_name --port $kubeapp_port --overrides '{ "apiVersion": "v1","spec":{"ports": [{"port":'"$kubeapp_port"',"targetPort":'"$kubeapp_port"',"nodePort":'"$kubeapp_node_port"',"protocol":"TCP"}]}}'
# Method 2:
# kubectl create service nodeport $kubeapp_service_name --tcp=$kubeapp_port:$kubeapp_port --node-port=$kubeapp_node_port
# kubectl set selector service $kubeapp_service_name app=$kubeapp_deployment_name
# Method 3:

# kubectl apply -f "$HOME/$dest_config_dir"
while ! kubectl apply -f "$HOME/$dest_config_dir"; do
    echo "--------"
    echo "If ingress controller is being installed it may take some time before it starts responding (60 sec)."
    echo "Will retry cubectl apply in 5 sec..."
    sleep 5
done

# Wait for kubernetes to start all the pods.
# NOTE, we can also wait like this:
# kubectl wait --for=condition=Ready pod/<podname>
echo "Waiting for all pods to start running..."
check_pods_status=true
test_pods_count=$(wc -l < "$test_pod_names_path")
while $check_pods_status; do
    check_pods_status=false
    # Display expected test pods.
    echo "-------- Expected running pods:"
    for ((test_pod_index=1; test_pod_index<=test_pods_count; test_pod_index++)); do
        # On Windows new line will have '\r' so we remove it here.
        echo $(awk 'FNR == '"$test_pod_index"' {print $1}' "$test_pod_names_path"| tr -d '\r')
    done
    echo "--------"
    # Display all detected pods.
    pods_status=$(kubectl get pods --all-namespaces --output=jsonpath='{range .items[*]}{@.status.phase}{" "}{@.metadata.name}{"\n"}{end}')
    echo "-------- Pod Status:"
    echo "$pods_status"
    pods_count=$(echo "$pods_status" | wc -l)
    # Check if all test pods are detected.
    for ((test_pod_index=1; test_pod_index<=test_pods_count; test_pod_index++)); do
        # On Windows new line will have '\r' so we remove it here.
        test_pod_name=$(awk 'FNR == '"$test_pod_index"' {print $1}' "$test_pod_names_path" | tr -d '\r')
        test_pod_found=false
        for ((pod_index=1; pod_index<=pods_count; pod_index++)); do
            deployment_pod_name=$(echo "$pods_status" | awk 'FNR == '"$pod_index"' {print $2}' -)
            if [[ "$deployment_pod_name" == "$test_pod_name"* ]]; then
                test_pod_found=true
                break
            fi
        done
        if ! $test_pod_found; then
            check_pods_status=true
            break
        fi
    done
    if $check_pods_status; then
        echo "--------"
        sleep 5
        continue
    fi
    echo "All expected pods detected."
    # Check if all pods are running.
    deployment_pod_found=false
    # TODO: instead of this for loop, just have awk return number of lines that do not match "Running" status?
    for ((pod_index=1; pod_index<=pods_count; pod_index++)); do
        pod_status=$(echo "$pods_status" | awk 'FNR == '"$pod_index"' {print $1}' -)
        #echo "$pod_status"
        if [[ "$pod_status" != "Running" && "$pod_status" != "Succeeded" ]]; then
            echo "--------"
            sleep 5
            check_pods_status=true
            break
        fi
    done
done
echo "All pods are running."
echo "--------"

# Wait for endpoints to return correct HTTP codes.
echo "Waiting for endpoints to respond..."
check_http_code=true
test_endpoints_count=$(wc -l < "$test_endpoints_path")
while $check_http_code; do
    echo "-------- Expected endpoint HTTP codes:"
    for ((endpoint_index=1; endpoint_index<=test_endpoints_count; endpoint_index++)); do
        # On Windows new line will have '\r' so we remove it here.
        endpoint_port_and_path=$(awk 'FNR == '"$endpoint_index"' {print $1}' "$test_endpoints_path" | tr -d '\r')
        endpoint_http_code=$(awk 'FNR == '"$endpoint_index"' {print $2}' "$test_endpoints_path" | tr -d '\r')
        echo "Endpoint http://127.0.0.1:$endpoint_port_and_path expected HTTP response: $endpoint_http_code"
    done
    echo "--------"
    echo "-------- Actual endpoint HTTP codes:"
    check_http_code=false
    for ((endpoint_index=1; endpoint_index<=test_endpoints_count; endpoint_index++)); do
        # On Windows new line will have '\r' so we remove it here.
    	endpoint_port_and_path=$(awk 'FNR == '"$endpoint_index"' {print $1}' "$test_endpoints_path" | tr -d '\r')
    	endpoint_http_code=$(awk 'FNR == '"$endpoint_index"' {print $2}' "$test_endpoints_path" | tr -d '\r')
        http_code=$(curl --write-out '%{http_code}' --fail --silent --insecure --output /dev/null "http://127.0.0.1:$endpoint_port_and_path" || true)
        echo "Endpoint http://127.0.0.1:$endpoint_port_and_path HTTP response: $http_code"
        if [[ "$http_code" != "$endpoint_http_code" ]]; then
            echo "--------"
            check_http_code=true
            sleep 5
            break
        fi
    done
done
echo "All endpoints responding."
echo "--------"

echo "Finished loading services and running tests."

###############################################################################
###############################################################################

sudo kubeadm reset

# NOTE: $cluster_address_prefix could be 10.0.0.0/8, so we delete both for clarity.
# We will set them again in the initialization script.
sudo ufw delete allow from 10.0.0.0/8
sudo ufw delete allow from $cluster_address_prefix
sudo ufw delete allow from $kube_control_plane_endpoint

if [[ $azure_generalize == "generalize" ]]; then
    #sudo waagent -deprovision+user
    sudo waagent -deprovision
fi

# To rerun script, so kubeadm init can be rerun:
# sudo kubeadm reset
# And remove control-plane-endpoint line from /etc/hosts

# To verify Kubernetes is working:
# kubectl get pod --all-namespaces -o wide
# kubectl get deployment
# kubectl get service

echo "###############################################################################"
echo "Finished Kubernetes Installation Script."
echo "###############################################################################"
