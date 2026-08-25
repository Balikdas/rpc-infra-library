# How to Configure Kubectl Autocompletion

This proceudre will install bash completion for Kubectl on Linux.

## Prerequisites

* The `kubectl` utility installed on your system
* The `bash-completion` package installed on your system

## Procedure

* Run the following command as your local user account:

```bash
kubectl completion bash | sudo tee /etc/bash_completion.d/kubectl > /dev/null
```

* Setup an alias for kubectl

```bash
echo 'alias k=kubectl' >>~/.bashrc
```

* Enable autocompletion for the alias

```bash
echo 'complete -o default -F __start_kubectl k' >>~/.bashrc
```

* Logout and login again, you should now be able to autocomplete kubectl commands with double `TAB`
