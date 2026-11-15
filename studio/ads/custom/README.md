# Custom

A scene Claude writes for one ad from the owner's own words in the Ad Maker. It is not a template: each one lives in
`jobs/ads/{id}/scene.html` and the storyboard points at it with `"template"`.

The scene loads the runtime with `<script src="s4f:runtime"></script>` (the filmer swaps in the real path), puts words in
`.words` elements inside `.safe`, and draws through `S4F.setup((t) => ...)`. Every picture depends only on `t`.
List every line that appears on screen in the storyboard's `frames`, so the brain check reads them.
