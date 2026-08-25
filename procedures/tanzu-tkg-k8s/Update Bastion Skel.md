# Procedure to Update Skel on Bastion Servers

This procedure is used to update the Skel on Bastion servers, for example when the Tanzu version changes or when there are changes required on the default `.bash_profile`

- Update JWT Authenticator (patch request-audience to match cluster name in mgmt cluster)
- Regen mgmt cluster kubeconfig with:

`tanzu cluster kubeconfig get -n tkg-system ${mgmt_cluster_name} --export-file=/var/tmp/kubeconfigs/${mgmt_cluster_name}-kubeconfig.yaml`

- Make the kubeconfig world readable:

`chmod a+r /var/tmp/kubeconfigs/*`

- Update `/etc/skel/.bash_profile`
- Backup the `.bash_profile` of all users
- Overwrite the `.bash_profile` of all users with the new one from `/etc/skel`
- Remove the `.config/tanzu` directory of all users

The scripted commands are below. Replace the first echo commmand with the content of the most recent bastion skel for your environment:

```bash
echo '# .bash_profile

# Get the aliases and functions
if [ -f ~/.bashrc ]; then
        . ~/.bashrc
fi

# User specific environment and startup programs
export PATH=$PATH:/usr/local/bin
alias k=kubectl
complete -o default -F __start_kubectl k

# Initialize Tanzu CLI if not already done
if [[ ! -d ~/.config/tanzu ]]; then
  echo "
Initializing Tanzu CLI environment on first login...
"
  tanzu config set env.TANZU_CLI_CEIP_OPT_IN_PROMPT_ANSWER yes
  tanzu config set env.TKG_CUSTOM_IMAGE_REPOSITORY harbor.cc.net.rogers.com/registry
  tanzu config eula accept
  tanzu init
  tanzu plugin install --group vmware-tkg/default:v2.3.1
  tanzu plugin sync
  echo "
Tanzu CLI initialization complete.
"
fi

# Create .kube dir if it does not exist
if [[ ! -d ~/.kube ]]; then
  mkdir -m 700 ~/.kube
  echo "Welcome to $(hostname -s)!"
  echo "
As this is your first login you may want to add your kubeconfig file in
the .kube directory. A kubeconfig is a YAML file that defines the login
parameters to your K8s cluster, which you would have received from Cloud
Engineering when your cluster was created.

To create your kubeconfig run the command:

vi ~/.kube/config

and paste the content of the kubeconfig file provided by Cloud Engineering.
Then you can run the 'kubectl' command to access your Kubernetes cluster.

The name Kubernetes originates from Greek, meaning helmsman or pilot. K8s as
an abbreviation results from counting the eight letters between the K and the s.

Welcome aboard sailor!
"

fi
' | sudo tee /etc/skel/.bash_profile

# Pause here to enter sudo password

ctx=$(kubectl config get-contexts --no-headers | grep rncc-k8s | grep -v tanzu | tr -d '*' | awk '{print $1}')
cluster=$(echo $ctx | awk -F@ '{print $2}')
kubectl config use $ctx
kubectl patch jwtauthenticators tkg-jwt-authenticator --type=merge -p "{\"spec\": { \"audience\": \"`echo $cluster`\"}}"
tanzu cluster kubeconfig get -n tkg-system $cluster --export-file=/var/tmp/kubeconfigs/$cluster-kubeconfig.yaml
chmod a+r /var/tmp/kubeconfigs/*

# Logout and log back in then run this:

for user in $(ls -1 /home); do
  sudo cp -p /home/$user/.bash_profile /home/$user/.bash_profile.bak
  sudo cp -p /etc/skel/.bash_profile /home/$user/.bash_profile
  sudo chown $user:domain\ users /home/$user/.bash_profile
  sudo rm -rf /home/$user/.config/tanzu
done
```
