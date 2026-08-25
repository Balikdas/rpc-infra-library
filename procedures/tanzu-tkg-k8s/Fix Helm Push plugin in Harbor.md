# Fix Helm Push Plugin in Harbor

The default helm push plugin does not get installed properly by the airgap scripts. Run the below to fix it:

```bash
helm plugin install --version v0.9.0 https://github.com/chartmuseum/helm-push.git
cd airgap/scripts/
bin/run.sh sync && tail -f ../logs/publish-helm-progress.log
bin/run.sh cancel
```
