# Configure VCSA to Use Proxy

This procedure illustrates how to configure a VCSA server to use proxy for internet connection which is requried for all VCSA's in the SDE network.

## Configure Proxy

- SSH as root the the VCSA server
- Edit `etc/sysconfig/proxy` file and add/replace the following variables:

  - Production:

    ```bash
    PROXY_ENABLED="yes"
    HTTP_PROXY="http://rncc-proxy-min.mgslb.net.rogers.com:80/"
    HTTPS_PROXY="http://rncc-proxy-min.mgslb.net.rogers.com:80/"
    NO_PROXY="localhost, 127.0.0.1, cc.net.rogers.com"
    ```

  - Lab:

    ```bash
    PROXY_ENABLED="yes"
    HTTP_PROXY="http://rncc-proxy-min.mgslb.vf.rogers.com:80/"
    HTTPS_PROXY="http://rncc-proxy-min.mgslb.vf.rogers.com:80/"
    NO_PROXY="localhost, 127.0.0.1, cc.vf.rogers.com"
    ```

- Reboot the VCSA server
