# Initial Splash

## Background/Goal

Show the VinTib moving logo once when a browser tab first enters the app from a link, then continue to the requested route after the GIF has played.

## Work

Add a small app-level splash overlay in `App.vue` using `vintib_moving_logo.gif`. Track display with `sessionStorage` so it runs once per tab and does not replay during in-app navigation.

## Checklist

- [x] Import `vintib_moving_logo.gif` in the app root.
- [x] Show a full-viewport splash only when the tab has not seen it yet.
- [x] Hide the splash after one GIF run and mark it as seen in `sessionStorage`.
- [x] Verify type-check/build.
