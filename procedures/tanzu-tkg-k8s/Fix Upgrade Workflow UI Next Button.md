# Fix for TCA Cluster Upgrade Workflow UI Next Button Stuck with Spinner

If you are trying to ugprade a workload cluster in TCA and the Workflow UI 'Next' button is greyed out and the spinner is active apply the fix below.

- Open the TCA UI and login
- Press F12 to open the browser developer console
- Navigate to "Console"
- In the console type `allow pasting` and press enter
- Paste the below code into the console and press enter:

```javascript
(function() {
 const origOpen = XMLHttpRequest.prototype.open;
 XMLHttpRequest.prototype.open = function(method, url) {
  if (typeof url === 'string' && url.includes('/vims') && !url.includes('page_size')) {
  const u = new URL(url, window.location.origin);
  u.searchParams.set('nextpage_opaque_marker', 'page_no=1,page_size=500');
  url = u.toString();
  }
  return origOpen.apply(this, arguments);
 };
 console.log('[TCA Workaround] VIM pagination patch applied — page_size=500 active.');
})();
```

- Initiate the cluster upgrade as normal

**Note:** This is a temporary workaround and needs to be applied to every new browser session.
